import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream, HLSStream

API_URL = "https://www.zhanqi.tv/api/static/v2.1/room/domain/{0}.json"

STATUS_ONLINE = 4
STATUS_OFFLINE = 0

_url_re = re.compile(r"""
    http(s)?://(www\.)?zhanqi.tv
    /(?P<channel>[^/]+)
""", re.VERBOSE)

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

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        res = self.session.http.get(API_URL.format(channel))
        room = self.session.http.json(res, schema=_room_schema)
        if not room:
            self.logger.info("Not a valid room url.")
            return

        if room["status"] != STATUS_ONLINE:
            self.logger.info("Stream currently unavailable.")
            return

        url = "http://wshdl.load.cdn.zhanqi.tv/zqlive/{room[videoId]}.flv?get_url=".format(room=room)
        stream = HTTPStream(self.session, url)
        yield "live", stream

        url = "http://dlhls.cdn.zhanqi.tv/zqlive/{room[videoId]}_1024/index.m3u8?Dnion_vsnae={room[videoId]}".format(room=room)
        stream = HLSStream(self.session, url)
        yield "live", stream


__plugin__ = Zhanqitv
