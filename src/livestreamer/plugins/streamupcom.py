import re

from livestreamer.compat import urljoin
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

RTMP_URL = "rtmp://{0}/app/{1}"
BALANCING_REQUEST_URI = "https://streamup-lancer.herokuapp.com/api/redirect/{0}"

_url_re = re.compile("http(s)?://(\w+\.)?streamup.com/(?P<channel>[^/?]+)")
_flashvars_re = re.compile("flashvars\.(?P<var>\w+)\s?=\s?'(?P<value>[^']+)';")
_swf_url_re = re.compile("swfobject.embedSWF\(\s*\"(?P<player_url>[^\"]+)\",")

_schema = validate.Schema(
    validate.union({
        "vars": validate.all(
            validate.transform(_flashvars_re.findall),
            validate.transform(dict),
            {
                "channel": validate.text,
            }
        ),
        "swf": validate.all(
            validate.transform(_swf_url_re.search),
            validate.get("player_url"),
            validate.endswith(".swf")
        )
    })
)

class StreamupCom(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, schema=_schema)
        if not res:
            return

        stream_ip = http.get(BALANCING_REQUEST_URI.format(res["vars"]["channel"])).text

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": RTMP_URL.format(stream_ip, res["vars"]["channel"]),
            "pageUrl": self.url,
            "swfUrl": urljoin(self.url, res["swf"]),
            "live": True
        })
        return streams

__plugin__ = StreamupCom
