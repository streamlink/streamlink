import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream

log = logging.getLogger(__name__)

API_URL = "https://api.live.bilibili.com/room/v1/Room/playUrl"
ROOM_API = "https://api.live.bilibili.com/room/v1/Room/room_init?id={}"
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

_room_stream_list_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "durl": [{"url": validate.url()}]
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
        self.session.http.headers.update({'Referer': self.url})
        match = _url_re.match(self.url)
        channel = match.group("channel")
        res_room_id = self.session.http.get(ROOM_API.format(channel))
        room_id_json = self.session.http.json(res_room_id, schema=_room_id_schema)
        room_id = room_id_json['room_id']
        if room_id_json['live_status'] != SHOW_STATUS_ONLINE:
            return

        params = {
            'cid': room_id,
            'quality': '4',
            'platform': 'web',
        }
        res = self.session.http.get(API_URL, params=params)
        room = self.session.http.json(res, schema=_room_stream_list_schema)
        if not room:
            return

        for stream_list in room["durl"]:
            name = "source"
            url = stream_list["url"]
            # check if the URL is available
            log.trace('URL={0}'.format(url))
            r = self.session.http.get(url,
                                      retries=0,
                                      timeout=3,
                                      stream=True,
                                      acceptable_status=(200, 403, 404, 405))
            p = urlparse(url)
            if r.status_code != 200:
                log.error('Netloc: {0} with error {1}'.format(p.netloc, r.status_code))
                continue

            log.debug('Netloc: {0}'.format(p.netloc))
            stream = HTTPStream(self.session, url)
            yield name, stream


__plugin__ = Bilibili
