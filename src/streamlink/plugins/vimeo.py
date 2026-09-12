"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$metadata id
$metadata author
$metadata title
$notes Password protected streams are not supported
"""

import re
import time
from urllib.parse import urljoin, urlparse

from streamlink.exceptions import NoStreamsError, PluginError, StreamError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream, parse_m3u8
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)

URL_UPDATE_PERIOD = 10 * 60
URL_UPDATE_FAILED = 30


class VimeoAPI:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _schema_config(config):
        schema_cdns = validate.all(
            {
                "cdns": {
                    str: validate.all(
                        {validate.optional("url"): validate.url()},
                        validate.get("url"),
                    ),
                },
            },
            validate.get("cdns"),
        )
        schema_config = validate.Schema(
            {
                "request": {
                    "files": {
                        validate.optional("hls"): schema_cdns,
                        validate.optional("progressive"): [
                            validate.all(
                                {
                                    validate.optional("url"): validate.url(),
                                    "quality": str,
                                },
                                validate.union_get("quality", "url"),
                            ),
                        ],
                    },
                    validate.optional("text_tracks"): [
                        validate.all(
                            {
                                validate.optional("url"): str,
                                "lang": str,
                            },
                            validate.union_get("lang", "url"),
                        ),
                    ],
                },
                validate.optional("video"): validate.none_or_all(
                    {
                        "id": int,
                        "title": str,
                        "owner": {
                            "name": str,
                        },
                    },
                    validate.union_get(
                        "id",
                        ("owner", "name"),
                        "title",
                    ),
                ),
            },
            validate.union_get(
                ("request", "files", "hls"),
                ("request", "files", "progressive"),
                ("request", "text_tracks"),
                "video",
            ),
        )

        return schema_config.validate(config)

    def get_player_config(self, page_url):
        return self.session.http.get(
            page_url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string('.//script[contains(text(),"window.playerConfig")][1]/text()'),
                validate.none_or_all(
                    re.compile(r"^\s*window\.playerConfig\s*=\s*(?P<json>{.+?})\s*$"),
                    validate.none_or_all(
                        validate.get("json"),
                        validate.parse_json(),
                        validate.transform(self._schema_config),
                    ),
                ),
            ),
        )

    def get_config_url(self, page_url):
        jwt, api_url = self.session.http.get(
            "https://vimeo.com/_next/viewer",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "jwt": str,
                    "apiUrl": str,
                },
                validate.union_get("jwt", "apiUrl"),
            ),
        )
        uri = self.session.http.get(
            "https://vimeo.com/api/oembed.json",
            params={"url": page_url},
            schema=validate.Schema(
                validate.parse_json(),
                {validate.optional("uri"): str},
                validate.get("uri"),
            ),
        )
        if not uri:
            return

        player_config_url = urljoin(update_scheme("https://", api_url), uri)
        return self.session.http.get(
            player_config_url,
            params={"fields": "config_url"},
            headers={"Authorization": f"jwt {jwt}"},
            schema=validate.Schema(
                validate.parse_json(),
                {"config_url": validate.url()},
                validate.get("config_url"),
            ),
        )

    def get_config_url_event(self, event_id):
        return self.session.http.get(
            f"https://vimeo.com/event/{event_id}/embed",
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string('.//script[contains(text(),"var htmlString")][1]/text()'),
                validate.none_or_all(
                    re.compile(r"var htmlString\s*=\s*`(?P<html>.+?)`;", re.DOTALL),
                    validate.none_or_all(
                        validate.get("html"),
                        validate.parse_html(),
                        validate.xml_xpath_string(".//*[@data-config-url][1]/@data-config-url"),
                    ),
                ),
            ),
        )

    def get_stream_data(self, config_url):
        return self.session.http.get(
            config_url,
            schema=validate.Schema(
                validate.parse_json(),
                validate.transform(self._schema_config),
            ),
        )


class VimeoHLSStream(HLSStream):
    URL_UPDATE_PERIOD = 600
    URL_UPDATE_FAILED = 30

    def __init__(self, session, url, fetch_url_func, **kwargs):
        super().__init__(session, url, **kwargs)
        self._fetch_url_func = fetch_url_func
        self._url = url
        self._stream_id = "/".join(urlparse(url).path.split("/")[-3:])
        log.trace("Stream ID: %s", self._stream_id)
        self._url_expire = time.time() + self.URL_UPDATE_PERIOD

    @property
    def url(self) -> str:
        if time.time() > self._url_expire:
            try:
                self._url = self._fetch_url_func(self._stream_id)
                self.args["url"] = self._url
                self._url_expire = time.time() + self.URL_UPDATE_PERIOD
                log.trace("Stream %s has been updated", self._stream_id)
            except (PluginError, NoStreamsError, StreamError, OSError) as e:
                log.trace(
                    "Failed to re-fetch HLS URL: %s; reusing last known URL; Retry in %d sec",
                    e,
                    self.URL_UPDATE_FAILED,
                )
                self._url_expire = time.time() + self.URL_UPDATE_FAILED
        return super().url


@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/(?!event/).+"),
)
@pluginmatcher(
    name="event",
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/event/(?P<event_id>\d+)"),
)
@pluginmatcher(
    name="player",
    pattern=re.compile(r"https?://player\.vimeo\.com/video/\d+"),
)
class Vimeo(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = VimeoAPI(self.session)

    def _get_stream_data(self):
        if self.matches["player"]:
            return self.api.get_player_config(self.url)

        config_url = ""
        if self.matches["event"]:
            log.debug("Getting event config_url")
            config_url = self.api.get_config_url_event(self.match["event_id"])
        if not config_url:
            log.debug("Getting config_url")
            config_url = self.api.get_config_url(self.url)

        if not config_url:
            log.error("The content is not available")
            raise NoStreamsError

        return self.api.get_stream_data(config_url)

    def _get_hls_url(self, stream_id):
        hls, _progressive, _text_tracks, _metadata = self._get_stream_data()
        hls = hls or {}
        multivariant = None
        for hls_url in hls.values():
            res = self.session.http.get(hls_url)
            res.encoding = "utf-8"
            multivariant = parse_m3u8(res, parser=VimeoHLSStream.__parser__)
            break

        if not multivariant or not multivariant.playlists:
            raise StreamError("Missing HLS media playlist in updated HLS multivariant playlist")

        playlists = [x.uri for x in multivariant.playlists]
        playlists.extend([x.uri for playlist in multivariant.playlists for x in playlist.media if x.uri is not None])
        playlists = [x for x in playlists if isinstance(x, str) and x.endswith(stream_id)]
        if not playlists:
            log.trace("Stream URL hasn't been updated. Stream ID %s", stream_id)
            raise StreamError("Stream not found")

        return playlists[0]

    def _get_streams(self):
        data = self._get_stream_data()
        if not data:
            return

        hls, progressive, text_tracks, metadata = data
        if metadata:
            self.id, self.author, self.title = metadata

        streams = []
        hls = hls or {}
        for url in hls.values():
            if not url:
                continue
            streams.extend(VimeoHLSStream.parse_variant_playlist(self.session, url, fetch_url_func=self._get_hls_url).items())
            break

        streams.extend(
            (quality, HTTPStream(self.session, url))
            for quality, url in progressive or []
            if url and quality not in streams
        )  # fmt: skip

        if text_tracks and self.session.get_option("mux-subtitles"):
            substreams = {
                lang: HTTPStream(self.session, urljoin("https://vimeo.com/", url))
                for lang, url in text_tracks
                if url
            }  # fmt: skip
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
