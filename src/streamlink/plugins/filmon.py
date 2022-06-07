"""
$description Live local TV channels and video on-demand service. OTT service from FilmOn.
$url filmon.com
$type live, vod
$notes Some VODs are mp4 which may not stream, use -o to download
"""

import logging
import re
import time
from typing import Tuple

from streamlink.compat import is_py3, str, urlparse, urlunparse
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
            return super(FilmOnHLSStreamWorker, self)._fetch_playlist()
        except StreamError as err:
            # noinspection PyUnresolvedReferences
            if err.err.response.status_code in (403, 502):
                self.stream.watch_timeout = 0
                self.playlist_reload_time = 0
                log.debug("Force reloading the channel playlist on error: {0}".format(err))
            raise err


class FilmOnHLSStreamReader(HLSStreamReader):
    __worker__ = FilmOnHLSStreamWorker


class FilmOnHLS(HLSStream):
    __shortname__ = "hls-filmon"
    __reader__ = FilmOnHLSStreamReader

    def __init__(self, session_, url, api, channel=None, vod_id=None, quality="high", **args):
        if channel is None and vod_id is None:
            raise PluginError("Channel or vod_id must be set")

        super(FilmOnHLS, self).__init__(session_, url, **args)
        self.api = api
        self.channel = channel
        self.vod_id = vod_id
        self.quality = quality
        self._url = url
        self.watch_timeout = 0.0
        self._first_netloc = ""

    def _get_stream_data(self):
        if self.channel:
            log.debug("Reloading FilmOn channel playlist: {0}".format(self.channel))
            for s in self.api.channel(self.channel):
                yield s
        elif self.vod_id:
            log.debug("Reloading FilmOn VOD playlist: {0}".format(self.vod_id))
            for s in self.api.vod(self.vod_id):
                yield s

    @property
    def url(self):
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


class FilmOnAPI(object):
    channel_url = "https://www.filmon.com/ajax/getChannelInfo"
    vod_url = "https://vms-admin.filmon.com/api/video/movie?id={0}"

    ATTEMPTS = 5
    TIMEOUT = 0.75

    stream_schema = validate.all(
        {
            "quality": validate.text,
            "url": validate.url(),
            "watch-timeout": int,
        },
        validate.union_get("quality", "url", "watch-timeout")
    )

    def __init__(self, session):
        self.session = session

    def channel(self, channel):
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
                log.debug("Received invalid or non-JSON data, attempt {0}/{1}".format(num, self.ATTEMPTS))
                if num >= self.ATTEMPTS:
                    raise
                num = num + 1
                time.sleep(self.TIMEOUT)

    def vod(self, vod_id):
        return self.session.http.get(
            self.vod_url.format(vod_id),
            schema=validate.Schema(
                validate.parse_json(),
                {"response": {"streams": {validate.text: self.stream_schema}}},
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

    def __init__(self, url):
        super(Filmon, self).__init__(url)
        parsed = urlparse(self.url)
        if parsed.path.startswith("/channel/"):
            self.url = urlunparse(parsed._replace(path=parsed.path.replace("/channel/", "/tv/")))
        self.api = FilmOnAPI(self.session)

        if is_py3:
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

        return super(Filmon, cls).stream_weight(key)

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
                        for s in streams.items():
                            yield s
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
                    log.debug("Found cached channel ID: {0}".format(_id))
                else:
                    _id = self.session.http.get(self.url, schema=validate.Schema(
                        validate.transform(re.compile(r"""channel_id\s*=\s*(?P<q>['"]?)(?P<value>\d+)(?P=q)""").search),
                        validate.any(None, validate.get("value")),
                    ))
                    log.debug("Found channel ID: {0}".format(_id))
                    # do not cache a group url
                    if _id and not is_group:
                        self.cache.set(channel, _id, expires=self.TIME_CHANNEL)

            if _id is None:
                raise PluginError("Unable to find channel ID: {0}".format(channel))

            try:
                for quality, url, timeout in self.api.channel(_id):
                    yield quality, FilmOnHLS(self.session, url, self.api, channel=_id, quality=quality)
            except Exception:
                if channel and not channel.isdigit():
                    self.cache.set(channel, None, expires=0)
                    log.debug("Reset cached channel: {0}".format(channel))
                raise


__plugin__ = Filmon
