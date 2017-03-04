import hashlib
import re
import time
import uuid

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream

MAPI_URL = "https://m.douyu.com/html5/live?roomId={0}"
LAPI_URL = "https://coapi.douyucdn.cn/lapi/live/thirdPart/getPlay/{0}"
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2
STREAM_WEIGHTS = {
    "low": 540,
    "middle": 720,
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
            "live_url": validate.text
        })
    },
    validate.get("data")
)


class Douyutv(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "douyutv"

        return Plugin.stream_weight(stream)

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

        ts = int(time.time())

        sign = hashlib.md5(("lapi/live/thirdPart/getPlay/{0}?aid=pcclient&rate=0&time={1}9TUk5fjjUjg9qIMH3sdnh".format(channel, ts)).encode('ascii')).hexdigest()
        headers = {
            "auth": sign,
            "time": str(ts),
            "aid": "pcclient"
        }
        res = http.get(LAPI_URL.format(channel) + "?rate=0", headers=headers)
        room = http.json(res, schema=_lapi_schema)
        url = room["live_url"]
        stream = HTTPStream(self.session, url)
        yield "source", stream

        sign = hashlib.md5(("lapi/live/thirdPart/getPlay/{0}?aid=pcclient&rate=2&time={1}9TUk5fjjUjg9qIMH3sdnh".format(channel, ts)).encode('ascii')).hexdigest()
        headers = {
            "auth": sign,
            "time": str(ts),
            "aid": "pcclient"
        }
        res = http.get(LAPI_URL.format(channel) + "?rate=2", headers=headers)
        room = http.json(res, schema=_lapi_schema)
        url = room["live_url"]
        stream = HTTPStream(self.session, url)
        yield "middle", stream

        sign = hashlib.md5(("lapi/live/thirdPart/getPlay/{0}?aid=pcclient&rate=1&time={1}9TUk5fjjUjg9qIMH3sdnh".format(channel, ts)).encode('ascii')).hexdigest()
        headers = {
            "auth": sign,
            "time": str(ts),
            "aid": "pcclient"
        }
        res = http.get(LAPI_URL.format(channel) + "?rate=1", headers=headers)
        room = http.json(res, schema=_lapi_schema)
        url = room["live_url"]
        stream = HTTPStream(self.session, url)
        yield "low", stream


__plugin__ = Douyutv
