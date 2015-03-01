import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

SWF_URL = "http://www.gaminglive.tv/lib/flowplayer/flash/flowplayer.commercial-3.2.18.swf"
CHANNELS_API_URL = "http://api.gaminglive.tv/channels/{0}"
QUALITY_WEIGHTS = {
    "source": 5,
    "live": 5,
    "1080": 4,
    "720": 3,
    "480": 2,
    "medium": 2,
    "360": 1,
    "low": 1
}

_url_re = re.compile("""
    http(s)?://www\.gaminglive\.tv
    /channels/(?P<channel>[^/]+)
""", re.VERBOSE)
_quality_re = re.compile("[^/]+-(?P<quality>[^/]+)")

_channel_schema = validate.Schema(
    {
        validate.optional("state"): {
            "stream": {
                "qualities": [validate.text],
                "rootUrl": validate.url(scheme="rtmp")
            }
        }
    },
    validate.get("state")
)


class GamingLive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "gaminglive"

        return Plugin.stream_weight(key)

    def _get_quality(self, label):
        match = _quality_re.match(label)
        if match:
            return match.group("quality")

        return "live"

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        res = http.get(CHANNELS_API_URL.format(channel))
        json = http.json(res, schema=_channel_schema)
        if not json:
            return

        streams = {}
        for quality in json["stream"]["qualities"]:
            stream_name = self._get_quality(quality)
            stream = RTMPStream(self.session, {
                "rtmp": json["stream"]["rootUrl"],
                "playpath": quality,
                "pageUrl": self.url,
                "swfVfy": SWF_URL,
                "live": True
            })
            streams[stream_name] = stream

        return streams


__plugin__ = GamingLive
