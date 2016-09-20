import hashlib
import re
import time
import uuid

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
MAPI_URL = "https://m.douyu.com/html5/live?roomId={0}"
LAPI_URL = "https://www.douyu.com/lapi/live/getPlay/{0}"
LAPI_SECRET = "A12Svb&%1UUmf@hC"
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2
STREAM_WEIGHTS = {
    "low": 540,
    "middle": 720,
    "source": 1080
}

_url_re = re.compile("""
    http(s)?://(www\.)?douyu.com
    /(?P<channel>[^/]+)
""", re.VERBOSE)

_room_id_re = re.compile(r'"room_id"\s*:\s*(\d+),')
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
            "rtmp_url": validate.text,
            "rtmp_live": validate.text
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

        http.headers.update({'User-Agent': USER_AGENT})
        http.verify=False
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
            return

        if room["show_status"] != SHOW_STATUS_ONLINE:
            return

        ts = int(time.time() / 60)
        did = uuid.uuid4().hex.upper()
        sign = hashlib.md5(("{0}{1}{2}{3}".format(channel, did, LAPI_SECRET, ts)).encode("utf-8")).hexdigest()

        data = {
            "cdn": "ws",
            "rate": "0",
            "tt": ts,
            "did": did,
            "sign": sign
        }

        res = http.post(LAPI_URL.format(channel), data=data)
        room = http.json(res, schema=_lapi_schema)

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        stream = HTTPStream(self.session, url)
        yield "source", stream

        data = {
            "cdn": "ws",
            "rate": "2",
            "tt": ts,
            "did": did,
            "sign": sign
        }

        res = http.post(LAPI_URL.format(channel), data=data)
        room = http.json(res, schema=_lapi_schema)

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        stream = HTTPStream(self.session, url)
        yield "middle", stream

        data = {
            "cdn": "ws",
            "rate": "1",
            "tt": ts,
            "did": did,
            "sign": sign
        }

        res = http.post(LAPI_URL.format(channel), data=data)
        room = http.json(res, schema=_lapi_schema)

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        stream = HTTPStream(self.session, url)
        yield "low", stream

__plugin__ = Douyutv
