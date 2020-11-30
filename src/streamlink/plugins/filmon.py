import logging
import re
import time
from urllib.parse import urlparse, urlunparse

from streamlink.exceptions import PluginError, StreamError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, hls_playlist
from streamlink.stream.hls import HLSStreamReader, HLSStreamWorker, Sequence

log = logging.getLogger(__name__)


class FilmOnHLSStreamWorker(HLSStreamWorker):
    def reload_playlist(self):
        if self.closed:
            return

        self.reader.buffer.wait_free()
        log.debug("Reloading playlist")

        if self.stream.channel:
            parsed = urlparse(self.stream.url)
            if self.stream._first_netloc is None:
                # save the first netloc
                self.stream._first_netloc = parsed.netloc
            # always use the first saved netloc
            new_stream_url = parsed._replace(netloc=self.stream._first_netloc).geturl()
        else:
            new_stream_url = self.stream.url

        try:
            res = self.session.http.get(
                new_stream_url,
                exception=StreamError,
                retries=self.playlist_reload_retries,
                **self.reader.request_params)
        except StreamError as err:
            if (hasattr(self.stream, "watch_timeout")
                    and any(x in str(err) for x in ("403 Client Error",
                                                    "502 Server Error"))):
                self.stream.watch_timeout = 0
                self.playlist_reload_time = 0
                log.debug(f"Force reloading the channel playlist on error: {err}")
                return
            raise err

        try:
            playlist = hls_playlist.load(res.text, res.url)
        except ValueError as err:
            raise StreamError(err)

        if playlist.is_master:
            raise StreamError("Attempted to play a variant playlist, use "
                              "'hls://{0}' instead".format(self.stream.url))

        if playlist.iframes_only:
            raise StreamError("Streams containing I-frames only is not playable")

        media_sequence = playlist.media_sequence or 0
        sequences = [Sequence(media_sequence + i, s)
                     for i, s in enumerate(playlist.segments)]

        if sequences:
            self.process_sequences(playlist, sequences)


class FilmOnHLSStreamReader(HLSStreamReader):
    __worker__ = FilmOnHLSStreamWorker


class FilmOnHLS(HLSStream):
    __shortname__ = "hls-filmon"

    def __init__(self, session_, channel=None, vod_id=None, quality="high", **args):
        super().__init__(session_, None, **args)
        self.channel = channel
        self.vod_id = vod_id
        if self.channel is None and self.vod_id is None:
            raise ValueError("channel or vod_id must be set")
        self.quality = quality
        self.api = FilmOnAPI(session_)
        self._url = None
        self.watch_timeout = 0
        self._first_netloc = None

    def _get_stream_data(self):
        if self.channel:
            log.debug(f"Reloading FilmOn channel playlist: {self.channel}")
            data = self.api.channel(self.channel)
            yield from data["streams"]
        elif self.vod_id:
            log.debug(f"Reloading FilmOn VOD playlist: {self.vod_id}")
            data = self.api.vod(self.vod_id)
            for _, stream in data["streams"].items():
                yield stream

    @property
    def url(self):
        # If the watch timeout has passed then refresh the playlist from the API
        if int(time.time()) >= self.watch_timeout:
            for stream in self._get_stream_data():
                if stream["quality"] == self.quality:
                    self.watch_timeout = int(time.time()) + stream["watch-timeout"]
                    self._url = stream["url"]
                    return self._url
            raise StreamError("cannot refresh FilmOn HLS Stream playlist")
        else:
            return self._url

    def to_url(self):
        url = self.url
        expires = self.watch_timeout - time.time()
        if expires < 0:
            raise TypeError("Stream has expired and cannot be converted to a URL")
        return url

    def open(self):
        reader = FilmOnHLSStreamReader(self)
        reader.open()

        return reader


class FilmOnAPI:
    def __init__(self, session):
        self.session = session

    channel_url = "http://www.filmon.com/api-v2/channel/{0}?protocol=hls"
    vod_url = "http://www.filmon.com/vod/info/{0}"

    stream_schema = {
        "quality": validate.text,
        "url": validate.url(),
        "watch-timeout": int
    }
    api_schema = validate.Schema(
        {
            "data": {
                "streams": validate.any(
                    {validate.text: stream_schema},
                    [stream_schema]
                )
            }
        },
        validate.get("data")
    )

    def channel(self, channel):
        for _ in range(5):
            if _ > 0:
                log.debug("channel sleep {0}".format(_))
                time.sleep(0.75)

            # retry for 50X errors
            try:
                res = self.session.http.get(self.channel_url.format(channel))
                if res:
                    # retry for invalid response data
                    try:
                        return self.session.http.json(res, schema=self.api_schema)
                    except PluginError:
                        log.debug("invalid or non-JSON data received")
                        continue
            except Exception:
                log.debug("invalid server response")

        raise PluginError("Unable to find 'self.api.channel' for {0}".format(channel))

    def vod(self, vod_id):
        res = self.session.http.get(self.vod_url.format(vod_id))
        return self.session.http.json(res, schema=self.api_schema)


class Filmon(Plugin):
    url_re = re.compile(r"""(?x)https?://(?:www\.)?filmon\.(?:tv|com)/(?:
        (?:
            index/popout\?
            |
            (?:tv/)channel/(?:export\?)?
            |
            tv/(?!channel/)
            |
            channel/
            |
            (?P<is_group>group/)
        )(?:channel_id=)?(?P<channel>[-_\w]+)
    |
        vod/view/(?P<vod_id>\d+)-
    )""")

    _channel_id_re = re.compile(r"""channel_id\s*=\s*(?P<quote>['"]?)(?P<value>\d+)(?P=quote)""")
    _channel_id_schema = validate.Schema(
        validate.transform(_channel_id_re.search),
        validate.any(None, validate.get("value"))
    )

    quality_weights = {
        "high": 720,
        "low": 480
    }

    TIME_CHANNEL = 60 * 60 * 24 * 365

    def __init__(self, url):
        super().__init__(url)
        parsed = urlparse(self.url)
        if parsed.path.startswith("/channel/"):
            self.url = urlunparse(parsed._replace(path=parsed.path.replace("/channel/", "/tv/")))
        self.api = FilmOnAPI(self.session)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, key):
        weight = cls.quality_weights.get(key)
        if weight:
            return weight, "filmon"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        url_m = self.url_re.match(self.url)

        channel = url_m and url_m.group("channel")
        vod_id = url_m and url_m.group("vod_id")
        is_group = url_m and url_m.group("is_group")

        if vod_id:
            data = self.api.vod(vod_id)
            for _, stream in data["streams"].items():
                streams = HLSStream.parse_variant_playlist(self.session, stream["url"])
                if not streams:
                    yield stream["quality"], HLSStream(self.session, stream["url"])
                else:
                    yield from streams.items()
        else:
            if channel and not channel.isdigit():
                _id = self.cache.get(channel)
                if _id is None:
                    _id = self.session.http.get(self.url, schema=self._channel_id_schema)
                    log.debug(f"Found channel ID: {_id}")
                    # do not cache a group url
                    if _id and not is_group:
                        self.cache.set(channel, _id, expires=self.TIME_CHANNEL)
                else:
                    log.debug(f"Found cached channel ID: {_id}")
            else:
                _id = channel

            if _id is None:
                raise PluginError("Unable to find channel ID: {0}".format(channel))

            try:
                data = self.api.channel(_id)
                for stream in data["streams"]:
                    yield stream["quality"], FilmOnHLS(self.session, channel=_id, quality=stream["quality"])
            except Exception:
                if channel and not channel.isdigit():
                    self.cache.set(channel, None, expires=0)
                    log.debug(f"Reset cached channel: {channel}")

                raise


__plugin__ = Filmon
