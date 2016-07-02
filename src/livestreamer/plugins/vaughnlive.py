import random
import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

INFO_URL = "http://mvn.vaughnsoft.net/video/edge/mnv-{domain}_{channel}_{version}_{ms}-{ms}-{random}"

DOMAIN_MAP = {
    "breakers": "btv",
    "vapers": "vtv",
    "vaughnlive": "live",
}

_url_re = re.compile("""
    http(s)?://(\w+\.)?
    (?P<domain>vaughnlive|breakers|instagib|vapers).tv
    /(?P<channel>[^/&?]+)
""", re.VERBOSE)

_swf_player_re = re.compile('swfobject.embedSWF\("(/\d+/swf/[0-9A-Za-z]+\.swf)"')

def decode_token(token):
    return token.replace("0m0", "")

_schema = validate.Schema(
    validate.transform(lambda s: s.split(";:mvnkey-")),
    validate.length(2),
    validate.union({
        "server": validate.all(
            validate.get(0),
            validate.text
        ),
        "token": validate.all(
            validate.get(1),
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
        match = _swf_player_re.search(res.text)
        if match is None:
            return
        swfUrl = "http://vaughnlive.tv" + match.group(1)

        match = _url_re.match(self.url)
        params = match.groupdict()
        params["domain"] = DOMAIN_MAP.get(params["domain"], params["domain"])
        params["version"] = PLAYER_VERSION
        params["ms"] = random.randint(0, 999)
        params["random"] = random.random()
        info = http.get(INFO_URL.format(**params), schema=_schema)

        stream = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live".format(info["server"]),
            "app": "live?{0}".format(info["token"]),
            "swfVfy": swfUrl,
            "pageUrl": self.url,
            "live": True,
            "playpath": "{domain}_{channel}".format(**params),
        })

        return dict(live=stream)

__plugin__ = VaughnLive
