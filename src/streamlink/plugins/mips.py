import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_query
from streamlink.stream import RTMPStream

BALANCER_URL = "http://www.mips.tv:1935/loadbalancer"
PLAYER_URL = "http://mips.tv/embedplayer/{0}/1/500/400"
SWF_URL = "http://mips.tv/content/scripts/eplayer.swf"

_url_re = re.compile("http(s)?://(\w+.)?mips.tv/(?P<channel>[^/&?]+)")
_flashvars_re = re.compile("'FlashVars', '([^']+)'")
_rtmp_re = re.compile("redirect=(.+)")

_schema = validate.Schema(
    validate.transform(_flashvars_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.transform(parse_query),
            {
                "id": validate.transform(int),
                validate.optional("s"): validate.text
            }
        )
    )
)
_rtmp_schema = validate.Schema(
    validate.transform(_rtmp_re.search),
    validate.get(1),
)


class Mips(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        headers = {"Referer": self.url}
        url = PLAYER_URL.format(channel)
        res = http.get(url, headers=headers, schema=_schema)
        if not res or "s" not in res:
            return

        streams = {}
        server = http.get(BALANCER_URL, headers=headers, schema=_rtmp_schema)
        playpath = "{0}?{1}".format(res["s"], res["id"])
        streams["live"] = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live/{1}".format(server, playpath),
            "pageUrl": self.url,
            "swfVfy": SWF_URL,
            "conn": "S:OK",
            "live": True
        })

        return streams

__plugin__ = Mips
