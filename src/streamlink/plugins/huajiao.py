import base64
import re
import time
import uuid
import random
import json

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

STREAM_WEIGHTS = {
        "source": 1080
}    

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
HUAJIAO_URL = "http://www.huajiao.com/l/{}"
LAPI_URL = "http://g2.live.360.cn/liveplay?stype=flv&channel={}&bid=huajiao&sn={}&sid={}&_rate=xd&ts={}&r={}&_ostype=flash&_delay=0&_sign=null&_ver=13"

_url_re = re.compile("""
        http(s)?://(www\.)?huajiao.com
        /l/(?P<channel>[^/]+)
""", re.VERBOSE)

_room_sn_re = re.compile(r'"sn"\s*:\s*"(?P<sn>[a-zA-Z0-9_]+)"', re.VERBOSE)
_room_channel_re = re.compile(r'"channel"\s*:\s*"(?P<channel>[a-zA-Z0-9_]+)"', re.VERBOSE)

_room_sn_schema = validate.Schema(
        validate.all(
            validate.transform(_room_sn_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get('sn'),
                    validate.transform(str)
                    )
                )
            )
        )
_room_channel_schema = validate.Schema(
        validate.all(
            validate.transform(_room_channel_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get('channel'),
                    validate.transform(str)
                    )
                )
            )
        )

class Huajiao(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "Huajiao"

        return Plugin.stream_weight(stream)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        http.headers.update({"User-Agent": USER_AGENT})
        http.verify=False

        sn = http.get(HUAJIAO_URL.format(channel), schema=_room_sn_schema)
        channel_sid = http.get(HUAJIAO_URL.format(channel), schema=_room_channel_schema)
        
        sid = uuid.uuid4().hex.upper()

        encoded_json = http.get(LAPI_URL.format(channel_sid, sn, sid, time.time(), random.random())).content

        decoded_json = base64.decodestring(encoded_json[0:3] + encoded_json[6:]).decode('utf-8')
        video_data = json.loads(decoded_json)
        url = video_data['main']
        
        stream = HTTPStream(self.session, url)
        name = "source"
        yield name, stream

__plugin__ = Huajiao
