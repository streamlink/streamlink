import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import (
    HTTPStream, HLSStream
)

API_URL = "http://www.zhanqi.tv/api/static/live.roomid/{roomID[id]}.json"

STATUS_ONLINE = 4
STATUS_OFFLINE = 0

#hls source is not stable, lower priority
STREAM_WEIGHTS = {
        "live": 1080
}

_url_re = re.compile("""
    http(s)?://(www\.)?zhanqi.tv
    /(?P<channel>[^/]+)
""", re.VERBOSE)

_json_re = re.compile(r"window\.oPageConfig\.oRoom\s*=\s*({.+?});")

_roomID_schema = validate.Schema(
    validate.all(
        validate.transform(_json_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(parse_json),
                {
                    "id": validate.all(
                        validate.text,
                        validate.transform(int)
                    )
                }
            )
        )
    )
)

_room_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "status": validate.all(
                validate.text,
                validate.transform(int)
            ),
            "videoId": validate.text
        })
    },
    validate.get("data")
)


class Zhanqitv(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "zhanqitv"
        return Plugin.stream_weight(stream)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        roomID = http.get(self.url, schema=_roomID_schema)

        res = http.get(API_URL.format(roomID=roomID))
        room = http.json(res, schema=_room_schema)
        if not room:
            self.logger.info("Not a valid room url.")
            return

        if room["status"] != STATUS_ONLINE:
            self.logger.info("Stream current unavailable.")
            return

        hls_url = "http://dlhls.cdn.zhanqi.tv/zqlive/{room[videoId]}_1024/index.m3u8?Dnion_vsnae={room[videoId]}".format(room=room)
        hls_stream = HLSStream(self.session, hls_url)
        if hls_stream:
            yield "hls", hls_stream

        http_url = "http://wshdl.load.cdn.zhanqi.tv/zqlive/{room[videoId]}.flv?get_url=".format(room=room)
        http_stream = HTTPStream(self.session, http_url)
        if http_stream:
            yield "http", http_stream


__plugin__ = Zhanqitv
