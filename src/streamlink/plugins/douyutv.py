import hashlib
import re
import time

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream, HLSStream, RTMPStream

#new API and key from https://gist.github.com/spacemeowx2/629b1d131bd7e240a7d28742048e80fc by spacemeowx2
MAPI_URL = "https://m.douyu.com/html5/live?roomId={0}"
LAPI_URL = "https://coapi.douyucdn.cn/lapi/live/thirdPart/getPlay/{0}?cdn={1}&rate={2}"
LAPI_SECRET = "9TUk5fjjUjg9qIMH3sdnh"
VAPI_URL = "https://vmobile.douyu.com/video/getInfo?vid={0}"
SHOW_STATUS_ONLINE = 1
SHOW_STATUS_OFFLINE = 2
STREAM_WEIGHTS = {
    "low": 540,
    "medium": 720,
    "source": 1080
}

_url_re = re.compile(r"""
    http(s)?://
    (?:
        (?P<subdomain>.+)
        \.
    )?
    douyu.com/
    (?:
        show/(?P<vid>[^/&?]+)|
        (?P<channel>[^/&?]+)
    )
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

_vapi_schema = validate.Schema(
    {
        "data": validate.any(None, {
            "video_url": validate.text
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

    def _get_room_json(self, channel, rate):
        cdn = "ws" #cdns: ["ws", "tct", "ws2", "dl"]
        ts = int(time.time())
        sign = hashlib.md5("lapi/live/thirdPart/getPlay/{0}?aid=pcclient&cdn={1}&rate={2}&time={3}{4}".format(channel, cdn, rate, ts, LAPI_SECRET).encode("ascii")).hexdigest()
        headers = {
            "auth": sign,
            "time": str(ts),
            "aid": "pcclient"
        }
        res = http.get(LAPI_URL.format(channel, cdn, rate), headers=headers)
        room = http.json(res, schema=_lapi_schema)
        return room

    def _get_streams(self):
        match = _url_re.match(self.url)
        subdomain = match.group("subdomain")

        http.verify = False
        http.mount('https://', HTTPAdapter(max_retries=99))

        if subdomain == 'v':
            vid = match.group("vid")
            headers = {
                "User-Agent": useragents.ANDROID,
                "X-Requested-With": "XMLHttpRequest"
            }
            res = http.get(VAPI_URL.format(vid), headers=headers)
            room = http.json(res, schema=_vapi_schema)
            yield "source", HLSStream(self.session, room["video_url"])
            return

        #Thanks to @ximellon for providing method.
        channel = match.group("channel")
        http.headers.update({'User-Agent': useragents.CHROME})
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

        rate = [0, 2, 1]
        quality = ['source', 'medium', 'low']
        for i in range(0, 3, 1):
            room = self._get_room_json(channel, rate[i])
            url = room["live_url"]
            if 'rtmp:' in url:
                stream = RTMPStream(self.session, {
                        "rtmp": url,
                        "live": True
                        })
                yield quality[i], stream
            else:
                yield quality[i], HTTPStream(self.session, url)
            yield quality[i], HLSStream(self.session, room["hls_url"])


__plugin__ = Douyutv
