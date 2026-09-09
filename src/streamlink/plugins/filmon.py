"""
$description Live local TV channels and video on-demand service. OTT service from FilmOn.
$url filmon.com
$type live
$metadata author
$metadata category
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from streamlink.exceptions import PluginError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


if TYPE_CHECKING:
    from streamlink.session import Streamlink


log = getLogger(__name__)


class FilmOnHLS(HLSStream):
    __shortname__ = "hls-filmon"

    DEFAULT_WATCH_TIMEOUT = 30.0

    def __init__(
        self,
        session: Streamlink,
        url: str,
        *,
        api: FilmOnAPI,
        channel: str = "",
        quality: str = "",
        watch_timeout: float = DEFAULT_WATCH_TIMEOUT,
        **kwargs,
    ):
        if not channel:
            raise PluginError("Channel ID must be set")

        super().__init__(session, url, **kwargs)
        self.api = api
        self.channel = channel
        self.quality = quality
        self._next_reload = time.time() + watch_timeout
        self._url = url

    @property
    def url(self) -> str:
        now = time.time()
        if now >= self._next_reload:
            log.debug(f"Reloading FilmOn channel playlist: {self.channel}")

            streams = self.api.get_stream_data(self.channel)
            for quality, url, timeout in streams:
                if quality != self.quality:
                    continue
                self._next_reload = now + timeout
                self._url = urlunparse(urlparse(self._url)._replace(query=urlparse(url).query))
                break
            else:
                raise TypeError("Stream has expired and cannot be translated to a URL")

        return self._url


class FilmOnAPI:
    _API_APP_ID = "filmontv-plus"
    _API_APP_SECRET = "x2h0pgqq"

    _URL_API_INIT = "https://api.filmon.com/tv/api/init"
    _URL_API_CHANNELS = "https://api.filmon.com/tv/api/channels"
    _URL_API_CHANNEL = "https://api.filmon.com/tv/api/channel/{channel_id}"

    def __init__(self, session: Streamlink):
        self.session = session
        self._session_key = ""

    @property
    def session_key(self) -> str:
        if not self._session_key:
            self._session_key = self.session.http.post(
                self._URL_API_INIT,
                json={
                    "app_id": self._API_APP_ID,
                    "app_secret": self._API_APP_SECRET,
                    "session_key": None,
                },
                schema=validate.Schema(
                    validate.parse_json(),
                    {"session_key": str},
                    validate.get("session_key"),
                ),
            )
        return self._session_key

    def get_channel_id(self, alias: str) -> tuple[str, str, str] | None:
        return self.session.http.post(
            self._URL_API_CHANNELS,
            json={
                "session_key": self.session_key,
            },
            schema=validate.Schema(
                validate.parse_json(),
                [
                    {
                        "id": str,
                        "title": str,
                        "alias": str,
                        "group": str,
                    },
                ],
                validate.filter(lambda item: item["alias"] == alias),
                validate.get(0),
                validate.none_or_all(
                    validate.union_get(
                        "id",
                        "title",
                        "group",
                    ),
                ),
            ),
        )

    def get_stream_data(self, channel_id: str) -> list[tuple[str, str, float]]:
        return self.session.http.post(
            self._URL_API_CHANNEL.format(channel_id=channel_id),
            json={
                "session_key": self.session_key,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "streams": [
                        validate.all(
                            {
                                "quality": str,
                                "url": validate.url(),
                                "watch-timeout": validate.any(float, int),
                            },
                            validate.union_get(
                                "quality",
                                "url",
                                "watch-timeout",
                            ),
                        ),
                    ],
                },
                validate.get("streams"),
            ),
        )


@pluginmatcher(
    re.compile(
        r"https?://(?:\w+\.)?filmon\.(?:com|tv)/(?:v2/)?tv/(?P<alias>[^/?#]+)",
    ),
)
class Filmon(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = FilmOnAPI(self.session)
        self.session.options.set("hls-playlist-reload-time", "segment")

    def _get_streams(self):
        channel_data = self.api.get_channel_id(self.match["alias"])
        if not channel_data:
            return

        channel_id, self.author, self.category = channel_data
        streams = self.api.get_stream_data(channel_id)

        quality, url, watch_timeout = next(
            ((quality, url, watch_timeout) for quality, url, watch_timeout in streams if quality.lower() == "high"),
            next(iter(streams), ("", "", 0)),
        )
        if not url:
            return

        return FilmOnHLS.parse_variant_playlist(
            self.session,
            url,
            api=self.api,
            channel=channel_id,
            quality=quality,
            watch_timeout=watch_timeout,
        )


__plugin__ = Filmon
