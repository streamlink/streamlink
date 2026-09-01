"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$metadata id
$metadata author
$metadata title
$notes Password protected streams are not supported
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from streamlink.exceptions import PluginError, StreamError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import M3U8, HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


if TYPE_CHECKING:
    from streamlink.session import Streamlink


log = getLogger(__name__)


@dataclass
class VimeoAPIResponseStreamData:
    hls: dict[str, str] | None
    progressive: list[tuple[str, str]] | None
    text_tracks: list[tuple[str, str]] | None
    metadata: tuple[str, str, str] | None


class VimeoHLSStream(HLSStream):
    URL_UPDATE_PERIOD = 600
    URL_UPDATE_FAILED = 30

    multivariant: M3U8

    def __init__(self, session: Streamlink, url: str, api: VimeoAPI, **kwargs):
        super().__init__(session, url, **kwargs)
        self.api = api
        self._url = url
        self._stream_id = "/".join(urlparse(url).path.split("/")[-3:])
        log.trace("Stream ID: %s", self._stream_id)
        self._url_expire = time.time() + self.URL_UPDATE_PERIOD

    @property
    def url(self) -> str:
        if time.time() > self._url_expire:
            try:
                self._url = self.api.get_hls_url(self._stream_id)
                self.args["url"] = self._url
                self._url_expire = time.time() + self.URL_UPDATE_PERIOD
                log.trace("Stream %s has been updated", self._stream_id)
            except (PluginError, StreamError, OSError) as e:
                log.trace(
                    "Failed to re-fetch HLS URL: %s; reusing last known URL; Retry in %d sec",
                    e,
                    self.URL_UPDATE_FAILED,
                )
                self._url_expire = time.time() + self.URL_UPDATE_FAILED
        return super().url


class VimeoAPI:
    VIEWER_URL = "https://vimeo.com/_next/viewer"
    OEMBED_URL = "https://vimeo.com/api/oembed.json"
    EVENT_EMBED_URL = "https://vimeo.com/event/{id}/embed"
    PLAYER_URL = "https://player.vimeo.com/video/{id}"
    PLAYER_CONFIG_URL = "https://player.vimeo.com/video/{id}/config"

    def __init__(self, session: Streamlink, url: str, player: bool = False, event: str | None = None):
        self.session = session
        self.url = url
        self.player = player
        self.event = event

    _schema_cdns = validate.all(
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
    _schema_config = validate.Schema(
        {
            "request": {
                "files": {
                    validate.optional("hls"): _schema_cdns,
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
        validate.transform(lambda d: VimeoAPIResponseStreamData(*d)),
    )

    def _get_player_config(self):
        log.debug("Getting config from the player HTML")
        return self.session.http.get(
            self.url,
            headers={"Sec-GPC": "1"},
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string('.//script[contains(text(),"window.playerConfig")][1]/text()'),
                validate.none_or_all(
                    re.compile(r"^\s*window\.playerConfig\s*=\s*(?P<json>{.+?})\s*$"),
                    validate.none_or_all(
                        validate.get("json"),
                        validate.parse_json(),
                        self._schema_config,
                    ),
                ),
            ),
        )

    def _get_stream_config(self, config_url: str):
        log.debug("Getting stream config")
        log.trace("config_url=%s", config_url[:100])
        return self.session.http.get(
            config_url,
            schema=validate.Schema(
                validate.parse_json(),
                self._schema_config,
            ),
        )

    def _get_config_url(self):
        jwt, api_url = self.session.http.get(
            self.VIEWER_URL,
            acceptable_status=(200, 403),
            schema=validate.Schema(
                validate.any(
                    validate.all(
                        validate.parse_json(),
                        {
                            "jwt": str,
                            "apiUrl": str,
                        },
                        validate.union_get("jwt", "apiUrl"),
                    ),
                    validate.transform(lambda _: (None, None)),
                ),
            ),
        )
        if not jwt or not api_url:
            return
        uri = self.session.http.get(
            self.OEMBED_URL,
            params={"url": self.url},
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
                validate.any(
                    validate.all(
                        {"config_url": validate.url()},
                        validate.get("config_url"),
                    ),
                    validate.transform(lambda _: None),
                ),
            ),
        )

    def _get_config_url_event(self, event_id: str):
        log.debug("Getting event config_url")
        log.trace("event_id=%s", event_id)
        return self.session.http.get(
            self.EVENT_EMBED_URL.format(id=event_id),
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

    def get_stream_data(self) -> VimeoAPIResponseStreamData | None:
        if self.player:
            return self._get_player_config()

        config_url = ""
        if self.event is not None:
            config_url = self._get_config_url_event(self.event)
        if not config_url:
            config_url = self._get_config_url()

        if config_url:
            return self._get_stream_config(config_url)

        video_id = urlparse(self.url).path.split("/")[-1]
        if data := self._get_stream_config(self.PLAYER_CONFIG_URL.format(id=video_id)):
            return data

        self.url = self.PLAYER_URL.format(id=video_id)
        return self._get_player_config()

    def get_hls_url(self, stream_id: str):
        if not (stream_data := self.get_stream_data()):
            raise StreamError("Missing stream data")

        if not (hls_url := next(iter((stream_data.hls or {}).values()), None)):
            raise StreamError("Missing HLS multivariant playlist URL")

        streams = VimeoHLSStream.parse_variant_playlist(self.session, hls_url, api=self)
        multivariant = next((stream.multivariant for stream in streams.values()), None)
        if not multivariant or not multivariant.playlists:
            raise StreamError("Missing HLS media playlist in updated HLS multivariant playlist")

        playlists = [x.uri for x in multivariant.playlists]
        playlists.extend([x.uri for playlist in multivariant.playlists for x in playlist.media if x.uri is not None])
        playlists = [x for x in playlists if isinstance(x, str) and x.endswith(stream_id)]
        if not playlists:
            raise StreamError(f"Stream URL hasn't been updated. Stream ID {stream_id}")

        return playlists[0]


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
        self.api = VimeoAPI(
            session=self.session,
            url=self.url,
            player=bool(self.matches["player"]),
            event=self.match["event_id"] if self.matches["event"] else None,
        )

    def _get_streams(self):
        if not (data := self.api.get_stream_data()):
            log.error("The content is not available")
            return

        if data.metadata:
            self.id, self.author, self.title = data.metadata

        streams = []

        if hls_url := next(iter((data.hls or {}).values()), None):
            streams.extend(VimeoHLSStream.parse_variant_playlist(self.session, hls_url, api=self.api).items())

        streams.extend(
            (quality, HTTPStream(self.session, url))
            for quality, url in data.progressive or []
            if url and quality not in streams
        )

        if data.text_tracks and self.session.get_option("mux-subtitles"):
            substreams = {
                lang: HTTPStream(self.session, urljoin("https://vimeo.com/", url))
                for lang, url in data.text_tracks
                if url
            }  # fmt: skip
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
