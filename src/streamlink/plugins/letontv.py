import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

PLAYER_URL = "http://leton.tv/player.php"
SWF_URL = "http://files.leton.tv/jwplayer.flash.swf"

_url_re = re.compile("""
    http?://(\w+.)?leton.tv
    (?:
        /player\.php\?.*streampage=
    )?
    (?:
        /broadcast/
    )?
    (?P<streampage>[^/?&]+)
""", re.VERBOSE)
_js_var_re = re.compile("var (?P<var>\w+)\s?=\s?'?(?P<value>[^;']+)'?;")
_rtmp_re = re.compile("/(?P<app>[^/]+)/(?P<playpath>.+)")


def _parse_server_ip(values):
    octets = [
        values["a"] / values["f"],
        values["b"] / values["f"],
        values["c"] / values["f"],
        values["d"] / values["f"],
    ]

    return ".".join(str(int(octet)) for octet in octets)


_schema = validate.Schema(
    validate.transform(_js_var_re.findall),
    validate.transform(dict),
    {
        "a": validate.transform(int),
        "b": validate.transform(int),
        "c": validate.transform(int),
        "d": validate.transform(int),
        "f": validate.transform(int),
        "v_part": validate.text,
    },
    validate.union({
        "server_ip": validate.transform(_parse_server_ip),
        "path": validate.all(
            validate.get("v_part"),
            validate.transform(_rtmp_re.findall),
            validate.get(0)
        )
    })
)


class LetOnTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        info = http.get(PLAYER_URL, params=match.groupdict(), schema=_schema)
        if not info["path"]:
            return

        app, playpath = info["path"]
        stream = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/{1}".format(info["server_ip"], app),
            "playpath": playpath,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "live": True
        })

        return dict(live=stream)


__plugin__ = LetOnTV
