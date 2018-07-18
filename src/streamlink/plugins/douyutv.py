import re
import time
import hashlib

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate, useragents
from streamlink.stream import HTTPStream, HLSStream, RTMPStream

API_URL = "https://capi.douyucdn.cn/api/v1/{0}&auth={1}"
VAPI_URL = "https://vmobile.douyu.com/video/getInfo?vid={0}"
API_SECRET = "zNzMV1y4EMxOHS6I5WKm"
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

        self.session.http.verify = False
        self.session.http.mount('https://', HTTPAdapter(max_retries=99))

        if subdomain == 'v':
            vid = match.group("vid")
            headers = {
                "User-Agent": useragents.ANDROID,
                "X-Requested-With": "XMLHttpRequest"
            }
            res = self.session.http.get(VAPI_URL.format(vid), headers=headers)
            room = self.session.http.json(res, schema=_vapi_schema)
            yield "source", HLSStream(self.session, room["video_url"])
            return

        channel = match.group("channel")
        try:
            channel = int(channel)
        except ValueError:
            channel = self.session.http.get(self.url, schema=_room_id_schema)
            if channel is None:
                channel = self.session.http.get(self.url, schema=_room_id_alt_schema)

        self.session.http.headers.update({'User-Agent': useragents.WINDOWS_PHONE_8})
        cdns = ["ws", "tct", "ws2", "dl"]
        ts = int(time.time())
        suffix = "room/{0}?aid=wp&cdn={1}&client_sys=wp&time={2}".format(channel, cdns[0], ts)
        sign = hashlib.md5((suffix + API_SECRET).encode()).hexdigest()

        res = self.session.http.get(API_URL.format(suffix, sign))
        room = self.session.http.json(res, schema=_room_schema)
        if not room:
            self.logger.info("Not a valid room url.")
            return

        if room["show_status"] != SHOW_STATUS_ONLINE:
            self.logger.info("Stream currently unavailable.")
            return

        url = room["hls_url"]
        yield "source", HLSStream(self.session, url)

        url = "{room[rtmp_url]}/{room[rtmp_live]}".format(room=room)
        if 'rtmp:' in url:
            stream = RTMPStream(self.session, {
                "rtmp": url,
                "live": True
            })
            yield "source", stream
        else:
            yield "source", HTTPStream(self.session, url)

        multi_streams = {
            "middle": "low",
            "middle2": "medium"
        }
        for name, url in room["rtmp_multi_bitrate"].items():
            url = "{room[rtmp_url]}/{url}".format(room=room, url=url)
            name = multi_streams[name]
            if 'rtmp:' in url:
                stream = RTMPStream(self.session, {
                    "rtmp": url,
                    "live": True
                })
                yield name, stream
            else:
                yield name, HTTPStream(self.session, url)


__plugin__ = Douyutv
