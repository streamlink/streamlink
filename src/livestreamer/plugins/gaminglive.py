import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream

QUALITY_WEIGHTS = {
    "live": 3,
    "medium": 2,
    "low": 1,
}
CHANNELS_API = "http://api.gaminglive.tv/channels/{0}"
_url_re = re.compile("http(s)?://staging.gaminglive.tv/\#/channels/(?P<channel>[^/]+)", re.VERBOSE)


class GamingLive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "GamingLive"

        return Plugin.stream_weight(key)

    def _get_quality(self, label):
        quality_re = re.compile(self.channel + "-(?P<quality>[^/]+)")
        match = quality_re.match(label)
        if match:
            return match.group("quality")

        return "live"

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        self.channel = match.group("channel")

        if not self.channel:
            return

        streams = {}
        res = http.get(CHANNELS_API.format(self.channel))
        json = http.json(res)

        state = json['state']

        if not state:
            return

        stream = state['stream']

        if not stream:
            return

        rtmpBaseUrl = stream['rootUrl']

        if not rtmpBaseUrl:
            return

        qualities = stream['qualities']

        if not qualities:
            return

        for quality in qualities:
            stream = RTMPStream(self.session, {
                "rtmp": rtmpBaseUrl + "/" + quality,
                "pageUrl": self.url
            })
            streams[self._get_quality(quality)] = stream

        return streams


__plugin__ = GamingLive
