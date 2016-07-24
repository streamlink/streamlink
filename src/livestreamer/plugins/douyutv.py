import hashlib
import re
import time
import random
import string

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HTTPStream

USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36"
MAPI_URL = "http://m.douyu.com/html5/live?roomId={0}"
LAPI_URL = "http://www.douyu.com/lapi/live/getPlay/{0}"
LAPI_SECRET = "A12Svb&%1UUmf@hC"
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2

_url_re = re.compile("""
    http(s)?://(www\.)?douyu.com
    /(?P<channel>[^/]+)
""", re.VERBOSE)

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

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        http.headers.update({"User-Agent": USER_AGENT})
        res = http.get(MAPI_URL.format(channel))
        room = http.json(res, schema=_room_schema)
        if not room:
            return

        if room["show_status"] != SHOW_STATUS_ONLINE:
            return

        ts = int(time.time() / 60)
        did = ''.join([random.choice(string.ascii_uppercase + string.digits) for n in range(32)])
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

__plugin__ = Douyutv
