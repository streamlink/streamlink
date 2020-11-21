import base64
import json
import random
import re
import time
import uuid

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.useragents import CHROME as USER_AGENT
from streamlink.stream import (HLSStream, HTTPStream)

HUAJIAO_URL = "http://www.huajiao.com/l/{}"
LAPI_URL = "http://g2.live.360.cn/liveplay?stype=flv&channel={}&bid=huajiao&sn={}&sid={}&_rate=xd&ts={}&r={}" \
           "&_ostype=flash&_delay=0&_sign=null&_ver=13"

_url_re = re.compile(r"""
        http(s)?://(www\.)?huajiao.com
        /l/(?P<channel>[^/]+)
""", re.VERBOSE)

_feed_json_re = re.compile(r'^\s*var\s*feed\s*=\s*(?P<feed>{.*})\s*;', re.MULTILINE)

_feed_json_schema = validate.Schema(
    validate.all(
        validate.transform(_feed_json_re.search),
        validate.any(
            None,
            validate.all(
                validate.get('feed'),
                validate.transform(json.loads)
            )
        )
    )
)


class Huajiao(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        self.session.http.headers.update({"User-Agent": USER_AGENT})
        self.session.http.verify = False

        feed_json = self.session.http.get(HUAJIAO_URL.format(channel), schema=_feed_json_schema)
        if feed_json['feed']['m3u8']:
            stream = HLSStream(self.session, feed_json['feed']['m3u8'])
        else:
            sn = feed_json['feed']['sn']
            channel_sid = feed_json['relay']['channel']
            sid = uuid.uuid4().hex.upper()
            encoded_json = self.session.http.get(LAPI_URL.format(channel_sid, sn, sid, time.time(), random.random())).content
            decoded_json = base64.decodestring(encoded_json[0:3] + encoded_json[6:]).decode('utf-8')
            video_data = json.loads(decoded_json)
            stream = HTTPStream(self.session, video_data['main'])
        yield "live", stream


__plugin__ = Huajiao
