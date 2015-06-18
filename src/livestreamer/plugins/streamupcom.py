import re

from livestreamer.compat import urljoin
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

RTMP_URL = "rtmp://{0}/app/{1}"
STATUS_REQUEST_URI = "https://lancer.streamup.com/api/channels/{0}"
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
        channel_name = res["vars"]["channel"]
        swf_url = res["swf"]

        # Check if the stream is online
        res = http.get(STATUS_REQUEST_URI.format(channel_name), raise_for_status=False)
        if res.status_code == 404:
            return

        stream_ip = http.get(BALANCING_REQUEST_URI.format(channel_name)).text

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": RTMP_URL.format(stream_ip, channel_name),
            "pageUrl": self.url,
            "swfUrl": urljoin(self.url, swf_url),
            "live": True
        })
        return streams

__plugin__ = StreamupCom
