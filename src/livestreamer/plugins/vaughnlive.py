import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

INFO_URL = "http://mvn.vaughnsoft.net/video/edge/{domain}_{channel}"

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
_channel_not_found_re = re.compile("<title>Channel Not Found")


def decode_token(token):
    return token.replace("0m0", "")

_schema = validate.Schema(
    validate.transform(lambda s: s.split(";:mvnkey%")),
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
        if _channel_not_found_re.search(res.text):
            return

        match = _url_re.match(self.url)
        params = match.groupdict()
        params["domain"] = DOMAIN_MAP.get(params["domain"], params["domain"])
        info = http.get(INFO_URL.format(**params), schema=_schema)
        swfUrl = "http://vaughnlive.tv" + re.compile('swfobject.embedSWF\("(/\d+/swf/[0-9A-Za-z]+\.swf)"').findall(res.text)[0]

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
