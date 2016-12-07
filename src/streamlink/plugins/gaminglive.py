import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

SWF_URL = "http://www.gaminglive.tv/lib/flowplayer/flash/flowplayer.commercial-3.2.18.swf"
API_URL = "http://api.gaminglive.tv/{0}/{1}"
VOD_RTMP_URL = "rtmp://gamingfs.fplive.net/gaming/{0}/"
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
    http(s)?://(\w+\.)?gaminglive\.tv
    /(?P<type>channels|videos)/(?P<name>[^/]+)
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

_vod_schema = validate.Schema(
    {
        "name": validate.text,
        "channel_slug": validate.text,
        "title": validate.text,
        "created_at": validate.transform(int)
    },
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

    def _create_rtmp_stream(self, rtmp, playpath, live):
        return RTMPStream(self.session, {
                    "rtmp": rtmp,
                    "playpath": playpath,
                    "pageUrl": self.url,
                    "swfVfy": SWF_URL,
                    "live": live
                })

    def _get_live_streams(self, name):
        res = http.get(API_URL.format("channels", name))
        json = http.json(res, schema=_channel_schema)
        if not json:
            return

        streams = {}
        for quality in json["stream"]["qualities"]:
            streams[self._get_quality(quality)] = self._create_rtmp_stream(json["stream"]["rootUrl"], quality, True)

        return streams

    def _get_vod_streams(self, name):
        res = http.get(API_URL.format("videos", name))
        json = http.json(res, schema=_vod_schema)
        if not json:
            return

        streams = {}
        streams["source"] = self._create_rtmp_stream(VOD_RTMP_URL.format(json["channel_slug"]), json["name"], True)

        return streams

    def _get_streams(self):
        match = _url_re.match(self.url)
        type = match.group("type")

        if type == "channels":
            return self._get_live_streams(match.group("name"))
        elif type == "videos":
            return self._get_vod_streams(match.group("name"))

__plugin__ = GamingLive
