"""
$description Indonesian & international live TV channels and video on-demand service. OTT service from Vidio.
$url vidio.com
$type live
$metadata id
"""

from __future__ import annotations

import re
from base64 import b64encode
from threading import RLock
from time import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from streamlink.exceptions import StreamError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, parse_m3u8
from streamlink.utils.crypto import AES, pad
from streamlink.utils.data import search_dict


if TYPE_CHECKING:
    from streamlink.session import Streamlink


log = getLogger(__name__)


class VidioHLSStream(HLSStream):
    __shortname__ = "vidio-hls"

    def __init__(self, *args, api: VidioAPI, streamid: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = api
        self.streamid = streamid

    @property
    def url(self):
        if url := self.api.get_updated_stream_url(self.streamid):
            current = urlparse(self.args["url"])
            updated = urlparse(url)
            path = "/".join([*current.path.split("/")[:-2], *updated.path.split("/")[-2:]])
            self.args["url"] = urlunparse(current._replace(path=path))

        return super().url


class VidioAPI:
    _API_AUTH = "https://api.vidio.com/auth"
    _API_LIVESTREAMINGS_DETAIL = "https://api.vidio.com/api/livestreamings/{streamid}/detail"
    _API_LIVESTREAMINGS_STREAM = "https://api.vidio.com/livestreamings/{streamid}/stream?initialize=true"

    _API_KEY_PUBKEY = b"dPr0QImQ7bc5o9LMntNba2DOsSbZcjUh"
    _API_KEY_IV = b"C8RWsrtFsoeyCyPt"

    DEFAULT_EXPIRATION_TIME = 120

    def __init__(self, session: Streamlink, url: str, expiration_time: int = DEFAULT_EXPIRATION_TIME):
        self.session = session
        self.url = url

        self._lock = RLock()
        self._stream_url_cache: str = ""
        self._stream_url_expiration: float = -1.0
        self._expiration_time = expiration_time

        self._signature: tuple[str, str] | None = None
        self._api_key: str | None = None

    def get_signature(self) -> tuple[str, str]:
        if self._signature is not None:
            return self._signature

        stream_signature = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'streamSignature')][1]/text()"),
                validate.none_or_all(
                    validate.regex(re.compile(r"""self\.__next_f\.push\(\[\d+,\s*(?P<data>".+?")]\)""")),
                    validate.get("data"),
                    validate.parse_json(),
                    validate.transform(lambda s: re.sub(r"^[^\[]+", "", s)),
                    validate.parse_json(),
                    validate.transform(lambda data: next(search_dict(data, "streamSignature"), None)),
                    {
                        "clientId": str,
                        "signature": str,
                    },
                    validate.union_get("clientId", "signature"),
                ),
            ),
        )
        if not stream_signature:
            raise PluginError("Could not find stream signature")

        self._signature = stream_signature

        return stream_signature

    def get_api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key

        api_key = self.session.http.post(
            self._API_AUTH,
            schema=validate.Schema(
                validate.parse_json(),
                {"api_key": str},
                validate.get("api_key"),
            ),
        )

        cypher = AES.new(self._API_KEY_PUBKEY, AES.MODE_CBC, self._API_KEY_IV)
        padded = pad(api_key.encode("utf8"), AES.block_size)
        encrypted = cypher.encrypt(padded)
        encoded = b64encode(encrypted).decode("utf8")
        self._api_key = encoded

        return encoded

    def _query_api(self, url, /, schema, **kwargs):
        headers = kwargs.pop("headers", {})

        client, signature = self.get_signature()
        api_key = self.get_api_key()

        headers.update({
            "Origin": "https://www.vidio.com",
            "Referer": "https://www.vidio.com/",
            "x-api-key": api_key,
            "x-api-platform": "web-desktop",
            "x-client": client,
            "x-secure-level": "2",
            "x-signature": signature,
        })

        return self.session.http.get(url, headers=headers, schema=schema, **kwargs)

    def get_stream_url(self, streamid: str) -> str:
        stream_url = self._query_api(
            self._API_LIVESTREAMINGS_STREAM.format(streamid=streamid),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "attributes": {
                            "hls": validate.url(),
                        },
                    },
                },
                validate.get(("data", "attributes", "hls")),
            ),
        )
        self._stream_url_expiration = time() + self._expiration_time

        return stream_url

    def get_updated_stream_url(self, streamid: str) -> str:
        # prevent the worker threads of the separate video and audio streams to get a new URL at the same time
        with self._lock:
            if self._stream_url_expiration >= time():
                return self._stream_url_cache

            log.debug("Getting new HLS playlist URL...")

            try:
                url = self.get_stream_url(streamid)
            except PluginError as err:
                raise StreamError(f"Error while trying to update stream URL: {err}") from err

            res = self.session.http.get(url)
            res.encoding = "utf-8"
            multivariant = parse_m3u8(res, parser=VidioHLSStream.__parser__)
            if not multivariant.playlists:
                raise StreamError("Missing HLS media playlist in updated HLS multivariant playlist")

            self._stream_url_cache = multivariant.playlists[0].uri

            return self._stream_url_cache


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?vidio\.com/live/(?P<streamid>\d+)-"),
)
class Vidio(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = VidioAPI(self.session, self.url)

    def _get_streams(self):
        self.id = streamid = self.match["streamid"]
        if hls_url := self.api.get_stream_url(streamid):
            return VidioHLSStream.parse_variant_playlist(
                self.session,
                hls_url,
                api=self.api,
                streamid=streamid,
                ffmpeg_options={"format": "matroska"},
            )


__plugin__ = Vidio
