import re
import time
import hashlib

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream, HLSStream, RTMPStream

OAPI_URL = "http://open.douyucdn.cn/api/RoomApi/room/{0}"
LAPI_URL = "https://capi.douyucdn.cn/api/v1/{0}&auth={1}"
AUTH_STR = "room/{0}?aid=androidhd1&cdn={1}&client_sys=android&time={2}"
VAPI_URL = "https://vmobile.douyu.com/video/getInfo?vid={0}"
LAPI_SECRET = "Y237pxTx2In5ayGz"
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
_room_id_alt_re = re.compile(r'data-onlineid=(\d+)')

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
            "room_status": validate.all(
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
            "rtmp_live": validate.text,
            "hls_url": validate.text
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
        http.headers.update({'User-Agent': useragents.CHROME, 'Referer': self.url})
        try:
            channel = int(channel)
        except ValueError:
            channel = http.get(self.url, schema=_room_id_schema)
            if channel is None:
                channel = http.get(self.url, schema=_room_id_alt_schema)

        res = http.get(OAPI_URL.format(channel))
        room = http.json(res, schema=_room_schema)
        if not room:
            self.logger.info("Not a valid room url.")
            return

        if room["room_status"] != SHOW_STATUS_ONLINE:
            self.logger.info("Stream currently unavailable.")
            return

        #API by ERioK
        http.headers.update({'User-Agent': useragents.ANDROID})
        cdns = ['ws', 'ws2', 'tct', 'dl']
        api_url = AUTH_STR.format(channel, cdns[0], int(time.time()))
        sign = hashlib.md5((api_url + LAPI_SECRET).encode()).hexdigest()
        res = http.get(LAPI_URL.format(api_url, sign))
        room = http.json(res, schema=_lapi_schema)

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        yield 'live', HLSStream(self.session, room['hls_url'])
        if 'rtmp:' in url:
            stream = RTMPStream(self.session, {
                    "rtmp": url,
                    "live": True
                    })
            yield 'live', stream
        else:
            yield 'live', HTTPStream(self.session, url)


__plugin__ = Douyutv
