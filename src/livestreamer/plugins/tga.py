#coding: utf-8

import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_query
from livestreamer.stream import HLSStream, HTTPStream

CHANNEL_INFO_URL = "http://api.plu.cn/tga/streams/%s"
STREAM_INFO_URL = "http://info.zb.qq.com/?cnlid=%d&cmd=2&stream=%d&system=1&sdtfrom=113"

_url_re = re.compile("http://star\.longzhu\.(?:tv|com)/(m\/)?(?P<domain>[a-z0-9]+)");
_channel_schema = validate.Schema(
    {
        "data" : validate.any(None, {
            "channel" : validate.any(None, {
                "id" : validate.all(
                    validate.text,
                    validate.transform(int)
                ),
                "vid" : int
            })
        })
    },
    validate.get("data")
);
_qq_schema = validate.Schema({
    validate.optional("playurl"): validate.url(scheme="http")   
},
    validate.get("playurl")
)

STREAM_WEIGHTS = {
    "middle": 540,
    "source": 1080
}

class Tga(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in STREAM_WEIGHTS:
            return STREAM_WEIGHTS[stream], "tga"

        return Plugin.stream_weight(stream)

    def _get_channel_id(self, domain):
        channel_info = http.get(CHANNEL_INFO_URL % str(domain))
        info = http.json(channel_info, schema=_channel_schema)
        if info is None:
            return False
        cnid = info['channel']['vid']
        if cnid <= 0:
            return False

        return cnid

    def _get_qq_stream_url(self, cnid, weight = 1):
        qq_stream_url = http.get(STREAM_INFO_URL % (int(cnid), int(weight)));
        qq_info = http.json(qq_stream_url, schema=_qq_schema)

        return qq_info;

    def _get_streams(self):
        match = _url_re.match(self.url);
        domain = match.group('domain')
        
        cnid = self._get_channel_id(domain);

        if cnid == False:
            return;

        flash_stream = HTTPStream(self.session, self._get_qq_stream_url(cnid, 1))
        if flash_stream:
            yield "live", flash_stream

        mobile_stream = HLSStream(self.session, self._get_qq_stream_url(cnid, 2))
        if mobile_stream:
            yield "live_http", mobile_stream

__plugin__ = Tga
