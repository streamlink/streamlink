import re
import logging
import time

from streamlink import StreamError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class FilmOnHLS(HLSStream):
    __shortname__ = "hls-filmon"

    def __init__(self, session_, channel=None, vod_id=None, quality="high", **args):
        super(FilmOnHLS, self).__init__(session_, None, **args)
        self.channel = channel
        self.vod_id = vod_id
        if self.channel is None and self.vod_id is None:
            raise ValueError("channel or vod_id must be set")
        self.quality = quality
        self.api = FilmOnAPI(session_)
        self._url = None
        self.watch_timeout = 0

    def _get_stream_data(self):
        if self.channel:
            log.debug("Reloading FilmOn channel playlist: {0}", self.channel)
            data = self.api.channel(self.channel)
            for stream in data["streams"]:
                yield stream
        elif self.vod_id:
            log.debug("Reloading FilmOn VOD playlist: {0}", self.vod_id)
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


class FilmOnAPI(object):
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
        res = self.session.http.get(self.channel_url.format(channel))
        return self.session.http.json(res, schema=self.api_schema)

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
            tv/(?!channel)
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
        super(Filmon, self).__init__(url)
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
                yield stream["quality"], FilmOnHLS(self.session, vod_id=vod_id, quality=stream["quality"])

        else:
            if channel and not channel.isdigit():
                _id = self.cache.get(channel)
                if _id is None:
                    _id = self.session.http.get(self.url, schema=self._channel_id_schema)
                    log.debug("Found channel ID: {0}", _id)
                    # do not cache a group url
                    if _id and not is_group:
                        self.cache.set(channel, _id, expires=self.TIME_CHANNEL)
                else:
                    log.debug("Found cached channel ID: {0}", _id)
            else:
                _id = channel

            try:
                data = self.api.channel(_id)
                for stream in data["streams"]:
                    yield stream["quality"], FilmOnHLS(self.session, channel=_id, quality=stream["quality"])
            except Exception:
                if channel and not channel.isdigit():
                    self.cache.set(channel, None, expires=0)
                    log.debug("Reset cached channel: {0}", channel)

                raise


__plugin__ = Filmon
