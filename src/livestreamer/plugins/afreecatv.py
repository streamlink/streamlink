import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_query
from livestreamer.stream import RTMPStream


VIEW_LIVE_API_URL = "http://api.afreeca.tv/live/view_live.php"

_url_re = re.compile("http(s)?://(\w+\.)?afreeca.tv/(?P<channel>[\w\-_]+)")
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
                "brt": validate.text,
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
