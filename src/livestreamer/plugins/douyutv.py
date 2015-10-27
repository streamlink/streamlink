import hashlib
import re
import time

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import (
    HTTPStream, HLSStream
)

API_URL = "http://www.douyutv.com/api/v1/room/{0}?aid=android&client_sys=android&time={1}&auth={2}"
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2
STREAM_WEIGHTS = {
    "middle": 540,
    "source": 1080
}

_url_re = re.compile("""
    http(s)?://(www\.)?douyutv.com
    /(?P<channel>[^/]+)
""", re.VERBOSE)

_room_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "show_status": validate.all(
                validate.text,
                validate.transform(int)
            ),
            "rtmp_url": validate.text,
            "rtmp_live": validate.text,
            "hls_url": validate.text,
            "rtmp_multi_bitrate": validate.all(
                validate.any([], {
                    validate.text: validate.text
                }),
                validate.transform(dict)
            )
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

        ts = int(time.time())
        sign = hashlib.md5(("room/{0}?aid=android&client_sys=android&time={1}".format(channel, ts) + "1231").encode("ascii")).hexdigest()

        res = http.get(API_URL.format(channel, ts, sign))
        room = http.json(res, schema=_room_schema)
        if not room:
            return

        if room["show_status"] != SHOW_STATUS_ONLINE:
            return

        hls_url = "{room[hls_url]}?wsiphost=local".format(room=room)
        hls_stream = HLSStream(self.session, hls_url)
        yield "hls", hls_stream

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        stream = HTTPStream(self.session, url)
        yield "source", stream

        for name, url in room["rtmp_multi_bitrate"].items():
            url = "{room[rtmp_url]}/{url}".format(room=room, url=url)
            stream = HTTPStream(self.session, url)
            yield name, stream

__plugin__ = Douyutv
