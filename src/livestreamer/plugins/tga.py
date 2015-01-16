#coding: utf-8

import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_query
from livestreamer.stream import HLSStream, HTTPStream

CHANNEL_INFO_URL = "http://api.plu.cn/tga/streams/%s"
ROOM_INFO_URL   = "http://star.api.plu.cn/api/roomstatus?roomid=%d&pageType=live"
STREAM_INFO_URL = "http://info.zb.qq.com/?cnlid=%d&cmd=2&stream=%d&system=1&sdtfrom=113"

_url_re = re.compile("http://star.(tga\.)?plu.cn/(m\/)?(?P<domain>[a-z0-9]+)");
_stream_re = re.compile("<iframe style='(.*?)' frameborder='0' scrolling='no' src='http://v.qq.com/iframe/live_player.html\?cnlid=(?P<cnid>\d+)&width=\d+&height=\d+'></iframe>");
_channel_schema = validate.Schema(
    {
        "data" : validate.any(None, {
            "channel" : validate.any(None, {
                "id" : validate.all(
                    validate.text,
                    validate.transform(int)
                )
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

_room_schame = validate.Schema({
    "Broadcast" : validate.any(None, {
        "Html": validate.text
    })
    },
    validate.get("Broadcast")
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

    def _get_channel_info(self, domain, weight=1):
        channel_info = http.get(CHANNEL_INFO_URL % str(domain))
        info = http.json(channel_info, schema=_channel_schema)
        if info is None:
            return False
        room_id = info['channel']['id']
        room_info = http.get(ROOM_INFO_URL % int(room_id))
        info = http.json(room_info, schema=_room_schame);
        if info is None:
            return False
        stream_url = info['Html']
        match = _stream_re.match(stream_url)
        if match is None:
            return False
        cnid = match.group('cnid');
        
        qq_stream_url = http.get(STREAM_INFO_URL % (int(cnid), int(weight)));
        qq_info = http.json(qq_stream_url, schema=_qq_schema)

        return qq_info;

    def _get_streams(self):
        match = _url_re.match(self.url);
        domain = match.group('domain')
        
        view_url = self._get_channel_info(domain, 1);

        if view_url == False:
            return;

        yield "source", HTTPStream(self.session, view_url)
        yield "middle", HLSStream(self.session, self._get_channel_info(domain, 2))

__plugin__ = Tga
