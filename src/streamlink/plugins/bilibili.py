import hashlib
import re
import time

from requests.adapters import HTTPAdapter
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream

API_URL = "http://live.bilibili.com/api/playurl?cid={0}&player=1&quality=0&sign={1}&otype=json"
ROOM_API = "https://api.live.bilibili.com/room/v1/Room/room_init?id={}"
API_SECRET = "95acd7f6cc3392f3"
SHOW_STATUS_OFFLINE = 0
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_ROUND = 2
STREAM_WEIGHTS = {
    "source": 1080
}

_url_re = re.compile(r"""
    http(s)?://live.bilibili.com
    /(?P<channel>[^/]+)
""", re.VERBOSE)

_room_id_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "room_id": int,
            "live_status": int
        })
    },
    validate.get("data")
)


class Bilibili(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "Bilibili"

        return Plugin.stream_weight(stream)

    def _get_streams(self):
        http.mount('https://', HTTPAdapter(max_retries=99))
        http.headers.update({'user-agent': useragents.CHROME})
        match = _url_re.match(self.url)
        channel = match.group("channel")
        res_room_id = http.get(ROOM_API.format(channel))
        room_id_json = http.json(res_room_id, schema=_room_id_schema)
        room_id = room_id_json['room_id']
        if room_id_json['live_status'] != SHOW_STATUS_ONLINE:
            return

        ts = int(time.time() / 60)
        sign = hashlib.md5(("{0}{1}".format(channel, API_SECRET, ts)).encode("utf-8")).hexdigest()

        res = http.get(API_URL.format(room_id, sign))
        room = http.json(res)
        if not room:
            return

        for stream_list in room["durl"]:
            name = "source"
            url = stream_list["url"]
            stream = HTTPStream(self.session, url)
            yield name, stream


__plugin__ = Bilibili
