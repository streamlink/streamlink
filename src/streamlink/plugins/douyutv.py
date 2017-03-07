import hashlib
import re
import time

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream, HLSStream

#new API and key from https://gist.github.com/spacemeowx2/629b1d131bd7e240a7d28742048e80fc by spacemeowx2
MAPI_URL = "https://m.douyu.com/html5/live?roomId={0}"
LAPI_URL = "http://coapi.douyucdn.cn/lapi/live/thirdPart/getPlay/{0}?rate={1}"

LAPI_SECRET = "9TUk5fjjUjg9qIMH3sdnh"

SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2
STREAM_WEIGHTS = {
    "low": 540,
    "medium": 720,
    "source": 1080
    }

_url_re = re.compile(r"""
    http(s)?://(www\.)?douyu.com
    /(?P<channel>[^/]+)
""", re.VERBOSE)

_room_id_re = re.compile(r'"room_id\\*"\s*:\s*(\d+),')
_room_id_alt_re = re.compile(r'data-room_id="(\d+)"')

_room_id_schema = validate.Schema(
    validate.all(
        validate.transform(_room_id_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_room_id_alt_schema = validate.Schema(
    validate.all(
        validate.transform(_room_id_alt_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_room_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "show_status": validate.all(
                validate.text,
                validate.transform(int)
            )
        })
    },
    validate.get("data")
)

_lapi_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "hls_url": validate.text,
            "live_url": validate.text
        })
    },
    validate.get("data")
)


class Douyutv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "douyutv"
        return Plugin.stream_weight(stream)

    #quality:
    # 0:source 2:medium 1:low
    def _get_room_json(self, channel, quality):
        ts = int(time.time())
        sign = hashlib.md5("lapi/live/thirdPart/getPlay/{0}?aid=pcclient&rate={1}&time={2}{3}".format(channel, quality, ts, LAPI_SECRET).encode('ascii')).hexdigest()
        data = {
            "auth": sign,
            "time": str(ts),
            "aid": 'pcclient'
        }

        res = http.get(LAPI_URL.format(channel, quality), headers=data)
        room = http.json(res, schema=_lapi_schema)
        return room

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        http.headers.update({'User-Agent': useragents.CHROME})
        http.verify = False
        http.mount('https://', HTTPAdapter(max_retries=99))

        #Thanks to @ximellon for providing method.
        try:
            channel = int(channel)
        except ValueError:
            channel = http.get(self.url, schema=_room_id_schema)
            if channel == 0:
                channel = http.get(self.url, schema=_room_id_alt_schema)

        res = http.get(MAPI_URL.format(channel))
        room = http.json(res, schema=_room_schema)
        if not room:
            self.logger.info("Not a valid room url.")
            return

        if room["show_status"] != SHOW_STATUS_ONLINE:
            self.logger.info("Stream currently unavailable.")
            return

        room_source = self._get_room_json(channel, 0)
        yield "source", HTTPStream(self.session, room_source['live_url'])
        yield "source", HLSStream(self.session, room_source['hls_url'])

        room_medium = self._get_room_json(channel, 2)
        yield "medium", HTTPStream(self.session, room_medium['live_url'])
        yield "medium", HLSStream(self.session, room_medium['hls_url'])

        room_low = self._get_room_json(channel, 1)
        yield "low", HTTPStream(self.session, room_low['live_url'])
        yield "low", HLSStream(self.session, room_low['hls_url'])
__plugin__ = Douyutv
