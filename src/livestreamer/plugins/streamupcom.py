import re

from livestreamer.compat import urljoin
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

RTMP_URL = "rtmp://{0}/app/{1}"
CHANNEL_DETAILS_URI = "https://api.streamup.com/v1/channels/{0}?access_token={1}"
REDIRECT_SERVICE_URI = "https://lancer.streamup.com/api/redirect/{0}"

_url_re = re.compile("http(s)?://(\w+\.)?streamup.com/(?P<channel>[^/?]+)")
_flashvars_re = re.compile("flashvars\.(?P<var>\w+)\s?=\s?'(?P<value>[^']+)';")
_swf_url_re = re.compile("swfobject.embedSWF\(\s*\"(?P<player_url>[^\"]+)\",")

_schema = validate.Schema(
    validate.union({
        "vars": validate.all(
            validate.transform(_flashvars_re.findall),
            validate.transform(dict),
            {
                "owner": validate.text,
                validate.optional("token"): validate.text
            }
        ),
        "swf": validate.all(
            validate.transform(_swf_url_re.search),
            validate.get("player_url"),
            validate.endswith(".swf")
        )
    })
)

_channel_details_schema = validate.Schema({
    "channel": {
        "live": bool,
        "slug": validate.text
    }
})

class StreamupCom(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, schema=_schema)
        if not res:
            return
        owner = res["vars"]["owner"]
        token = res["vars"].get("token", "null")
        swf_url = res["swf"]

        # Check if the stream is online
        res = http.get(CHANNEL_DETAILS_URI.format(owner, token))
        channel_details = http.json(res, schema=_channel_details_schema)
        if not channel_details["channel"]["live"]:
            return

        stream_ip = http.get(REDIRECT_SERVICE_URI.format(owner)).text

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": RTMP_URL.format(stream_ip, channel_details["channel"]["slug"]),
            "pageUrl": self.url,
            "swfUrl": urljoin(self.url, swf_url),
            "live": True
        })
        return streams

__plugin__ = StreamupCom
