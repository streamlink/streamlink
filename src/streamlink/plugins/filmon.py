"""
$description Live local TV channels and video on-demand service. OTT service from FilmOn.
$url filmon.com
$type live, vod
$notes Some VODs are mp4 which may not stream, use -o to download
"""

import logging
import re
import time
from typing import Iterator, List, Tuple
from urllib.parse import urlparse, urlunparse

from streamlink.exceptions import PluginError, StreamError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.http_session import TLSSecLevel1Adapter
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)

_StreamData = Tuple[str, str, int]


class FilmOnHLSStreamWorker(HLSStreamWorker):
    def _fetch_playlist(self):
        try:
            return super()._fetch_playlist()
        except StreamError as err:
            # noinspection PyUnresolvedReferences
            if err.err.response.status_code in (403, 502):
                self.stream.watch_timeout = 0
                self.playlist_reload_time = 0
                log.debug(f"Force-reloading the channel playlist on error: {err}")
            raise err


class FilmOnHLSStreamReader(HLSStreamReader):
    __worker__ = FilmOnHLSStreamWorker


class FilmOnHLS(HLSStream):
    __shortname__ = "hls-filmon"
    __reader__ = FilmOnHLSStreamReader

    def __init__(self, session_, url: str, api: "FilmOnAPI", channel=None, vod_id=None, quality="high", **args):
        if channel is None and vod_id is None:
            raise PluginError("Channel or vod_id must be set")

        super().__init__(session_, url, **args)
        self.api = api
        self.channel = channel
        self.vod_id = vod_id
        self.quality = quality
        self._url = url
        self.watch_timeout = 0.0
        self._first_netloc = ""

    def _get_stream_data(self) -> Iterator[_StreamData]:
        if self.channel:
            log.debug(f"Reloading FilmOn channel playlist: {self.channel}")
            yield from self.api.channel(self.channel)
        elif self.vod_id:
            log.debug(f"Reloading FilmOn VOD playlist: {self.vod_id}")
            yield from self.api.vod(self.vod_id)

    @property
    def url(self) -> str:
        if time.time() <= self.watch_timeout:
            return self._url

        # If the watch timeout has passed then refresh the playlist from the API
        for quality, url, timeout in self._get_stream_data():
            if quality == self.quality:
                self.watch_timeout = time.time() + timeout

                if not self.channel:
                    self._url = url
                else:
                    parsed = urlparse(url)
                    if not self._first_netloc:
                        # save the first netloc
                        self._first_netloc = parsed.netloc
                    # always use the first saved netloc
                    self._url = parsed._replace(netloc=self._first_netloc).geturl()

                return self._url

        raise TypeError("Stream has expired and cannot be translated to a URL")


class FilmOnAPI:
    channel_url = "https://www.filmon.com/ajax/getChannelInfo"
    vod_url = "https://vms-admin.filmon.com/api/video/movie?id={0}"

    ATTEMPTS = 5
    TIMEOUT = 0.75

    stream_schema = validate.all(
        {
            "quality": str,
            "url": validate.url(),
            "watch-timeout": int,
        },
        validate.union_get("quality", "url", "watch-timeout")
    )

    def __init__(self, session):
        self.session = session

    def channel(self, channel) -> List[_StreamData]:
        num = 1
        while True:
            # retry for 50X errors or validation errors at the same time
            try:
                return self.session.http.post(
                    self.channel_url,
                    data={
                        "channel_id": channel,
                        "quality": "low",
                    },
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    schema=validate.Schema(
                        validate.parse_json(),
                        {"streams": [self.stream_schema]},
                        validate.get("streams"),
                    ),
                )
            except PluginError:
                log.debug(f"Received invalid or non-JSON data, attempt {num}/{self.ATTEMPTS}")
                if num >= self.ATTEMPTS:
                    raise
                num = num + 1
                time.sleep(self.TIMEOUT)

    def vod(self, vod_id) -> List[_StreamData]:
        return self.session.http.get(
            self.vod_url.format(vod_id),
            schema=validate.Schema(
                validate.parse_json(),
                {"response": {"streams": {str: self.stream_schema}}},
                validate.get(("response", "streams")),
                validate.transform(lambda d: d.values()),
            ),
        )


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?filmon\.(?:tv|com)/
    (?:
        (?:
            index/popout\?
            |
            (?:tv/)?channel/(?:export\?)?
            |
            tv/(?!channel/)
            |
            channel/
            |
            (?P<is_group>group/)
        )(?:channel_id=)?(?P<channel>[-_\w]+)
        |
        vod/view/(?P<vod_id>[^/?&]+)
    )
""", re.VERBOSE))
class Filmon(Plugin):
    quality_weights = {
        "high": 720,
        "low": 480
    }

    TIME_CHANNEL = 60 * 60 * 24 * 365

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parsed = urlparse(self.url)
        if parsed.path.startswith("/channel/"):
            self.url = urlunparse(parsed._replace(path=parsed.path.replace("/channel/", "/tv/")))
        self.api = FilmOnAPI(self.session)

        adapter = TLSSecLevel1Adapter()
        self.session.http.mount("https://filmon.com", adapter)
        self.session.http.mount("https://www.filmon.com", adapter)
        self.session.http.mount("https://vms-admin.filmon.com/", adapter)

        self.session.options.set("hls-playlist-reload-time", "segment")

    @classmethod
    def stream_weight(cls, key):
        weight = cls.quality_weights.get(key)
        if weight:
            return weight, "filmon"

        return super().stream_weight(key)

    def _get_streams(self):
        channel = self.match.group("channel")
        vod_id = self.match.group("vod_id")
        is_group = self.match.group("is_group")

        # get cookies
        self.session.http.get(self.url)

        if vod_id:
            for quality, url, timeout in self.api.vod(vod_id):
                if url.endswith(".m3u8"):
                    streams = HLSStream.parse_variant_playlist(self.session, url)
                    if streams:
                        yield from streams.items()
                        return
                    yield quality, HLSStream(self.session, url)
                elif url.endswith(".mp4"):
                    yield quality, HTTPStream(self.session, url)
        else:
            if not channel or channel.isdigit():
                _id = channel
            else:
                _id = self.cache.get(channel)
                if _id is not None:
                    log.debug(f"Found cached channel ID: {_id}")
                else:
                    _id = self.session.http.get(self.url, schema=validate.Schema(
                        re.compile(r"""channel_id\s*=\s*(?P<q>['"]?)(?P<value>\d+)(?P=q)"""),
                        validate.any(None, validate.get("value")),
                    ))
                    log.debug(f"Found channel ID: {_id}")
                    # do not cache a group url
                    if _id and not is_group:
                        self.cache.set(channel, _id, expires=self.TIME_CHANNEL)

            if _id is None:
                raise PluginError(f"Unable to find channel ID: {channel}")

            try:
                for quality, url, timeout in self.api.channel(_id):
                    yield quality, FilmOnHLS(self.session, url, self.api, channel=_id, quality=quality)
            except Exception:
                if channel and not channel.isdigit():
                    self.cache.set(channel, None, expires=0)
                    log.debug(f"Reset cached channel: {channel}")
                raise


__plugin__ = Filmon
