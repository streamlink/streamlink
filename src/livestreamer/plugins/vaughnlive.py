import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

INFO_URL = "http://mvn.vaughnsoft.net/video/edge/live_{channel}"
SWF_URL = "http://vaughnlive.tv/800021294/swf/VaughnSoftPlayer.swf"

DEBUG_PORT_ID = 84
SECURE_TOKEN = "30dabc4871922a1314192e925ab7961d"
SET_GEO_CODE = 5

_url_re = re.compile("http(s)?://(\w+\.)?vaughnlive.tv/(?P<channel>[^/&?]+)")
_channel_not_found_re = re.compile("<title>Channel Not Found")


def decode_token(token):
    def decode_part(part):
        part = int(part.replace("0m0", ""))
        part /= DEBUG_PORT_ID
        part /= SET_GEO_CODE
        return chr(int(part))

    return "".join(decode_part(part) for part in token.split(":"))


_schema = validate.Schema(
    validate.transform(lambda s: s.split(";")),
    validate.length(3),
    validate.union({
        "server": validate.all(
            validate.get(0),
            validate.text
        ),
        "token": validate.all(
            validate.get(2),
            validate.text,
            validate.transform(decode_token)
        )
    })
)

class VaughnLive(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        if _channel_not_found_re.search(res.text):
            return

        match = _url_re.match(self.url)
        info = http.get(INFO_URL.format(**match.groupdict()), schema=_schema)

        stream = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live".format(info["server"]),
            "app": "live?{0}".format(info["token"]),
            "swfVfy": SWF_URL,
            "pageUrl": self.url,
            "live": True,
            "playpath": "live_{0}".format(match.group("channel")),
            "token": SECURE_TOKEN
        })

        return dict(live=stream)

__plugin__ = VaughnLive
