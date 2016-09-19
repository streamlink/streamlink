import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_query
from streamlink.stream import RTMPStream


VIEW_LIVE_API_URL = "http://api.afreeca.tv/live/view_live.php"
VIEW_LIVE_API_URL_TW = "http://api.afreecatv.com.tw/live/view_live.php"
VIEW_LIVE_API_URL_JP = "http://api.afreecatv.jp/live/view_live.php"

_url_re = re.compile("http(s)?://(\w+\.)?(afreecatv.com.tw|afreeca.tv|afreecatv.jp)/(?P<channel>[\w\-_]+)")
_url_re_tw = re.compile("http(s)?://(\w+\.)?(afreecatv.com.tw)/(?P<channel>[\w\-_]+)")
_url_re_jp = re.compile("http(s)?://(\w+\.)?(afreecatv.jp)/(?P<channel>[\w\-_]+)")
_flashvars_re = re.compile('<param name="flashvars" value="([^"]+)" />')

_flashvars_schema = validate.Schema(
    validate.transform(_flashvars_re.findall),
    validate.get(0),
    validate.transform(parse_query),
    validate.any(
        {
            "s": validate.text,
            "id": validate.text
        },
        {}
    )
)
_view_live_schema = validate.Schema(
    {
        "channel": {
            "strm": [{
                "bps": validate.text,
                "purl": validate.url(scheme="rtmp")
            }]
        },
    },
    validate.get("channel"),
    validate.get("strm")
)


class AfreecaTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        flashvars = http.get(self.url, schema=_flashvars_schema)
        if not flashvars:
            return

        params = {
            "rt": "json",
            "lc": "en_US",
            "pt": "view",
            "bpw": "",
            "bid": flashvars["id"],
            "adok": "",
            "bno": ""
        }
        
        if re.search(_url_re_tw, self.url):
            res = http.get(VIEW_LIVE_API_URL_TW, params=params)
        elif re.search(_url_re_jp, self.url):
            res = http.get(VIEW_LIVE_API_URL_JP, params=params)
        else:
            res = http.get(VIEW_LIVE_API_URL, params=params)
            
        streams = http.json(res, schema=_view_live_schema)

        for stream in streams:
            stream_name = "{0}p".format(stream["bps"])
            stream_params = {
                "rtmp": stream["purl"],
                "live": True
            }
            yield stream_name, RTMPStream(self.session, stream_params)


__plugin__ = AfreecaTV
