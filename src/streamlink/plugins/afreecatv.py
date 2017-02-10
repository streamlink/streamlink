import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_query
from streamlink.stream import RTMPStream


VIEW_LIVE_API_URL = "http://api.{region}/live/view_live.php"

_url_re = re.compile(r"https?://(\w+\.)?(?P<region>afreecatv\.com\.tw|afreeca\.tv|afreecatv\.jp)/(?P<channel>[\w\-_]+)")

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
        match = _url_re.match(self.url)

        params = {
            "pt": "view",
            "bid": match.group("channel")
        }

        res = http.get(VIEW_LIVE_API_URL.format(region=match.group("region")), params=params)

        streams = http.json(res, schema=_view_live_schema)

        for stream in streams:
            stream_name = "{0}p".format(stream["bps"])
            stream_params = {
                "rtmp": stream["purl"],
                "live": True
            }
            yield stream_name, RTMPStream(self.session, stream_params)


__plugin__ = AfreecaTV
