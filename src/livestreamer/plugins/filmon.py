import re

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

AJAX_HEADERS = {
    "Referer": "http://www.filmon.com",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
CHINFO_URL = "http://www.filmon.com/ajax/getChannelInfo"
VODINFO_URL = "http://www.filmon.com/vod/info/{0}"
QUALITY_WEIGHTS = {
    "high": 720,
    "low": 480
}
SWF_URL = "http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"


_url_re = re.compile("http(s)?://(\w+\.)?filmon.com/(channel|tv|vod)/")
_channel_id_re = re.compile("/channels/(\d+)/extra_big_logo.png")
_vod_id_re = re.compile("movie_id=(\d+)")

_channel_schema = validate.Schema({
    "streams": [{
        "name": validate.text,
        "quality": validate.text,
        "url": validate.url(scheme="rtmp")
    }]
})
_vod_schema = validate.Schema(
    {
        "data": {
            "streams": {
                validate.text: {
                    "name": validate.text,
                    "url": validate.url(scheme="rtmp")
                }
            }
        }
    },
    validate.get("data")
)


class Filmon(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "filmon"

        return Plugin.stream_weight(key)

    def _get_rtmp_app(self, rtmp):
        parsed = urlparse(rtmp)
        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        return app

    def _get_live_streams(self, channel_id):
        params = dict(channel_id=channel_id)
        res = http.post(CHINFO_URL, data=params, headers=AJAX_HEADERS)
        channel = http.json(res, schema=_channel_schema)

        streams = {}
        for stream in channel["streams"]:
            name = stream["quality"]
            rtmp = stream["url"]
            playpath = stream["name"]
            app = self._get_rtmp_app(rtmp)

            stream = RTMPStream(self.session, {
                "rtmp": rtmp,
                "pageUrl": self.url,
                "swfUrl": SWF_URL,
                "playpath": playpath,
                "app": app,
                "live": True
            })
            streams[name] = stream

        return streams

    def _get_vod_streams(self, movie_id):
        res = http.get(VODINFO_URL.format(movie_id), headers=AJAX_HEADERS)
        vod = http.json(res, schema=_vod_schema)

        streams = {}
        for name, stream_info in vod["streams"].items():
            rtmp = stream_info["url"]
            app = self._get_rtmp_app(rtmp)
            playpath = stream_info["name"]
            if playpath.endswith(".mp4"):
                playpath = "mp4:" + playpath

            stream = RTMPStream(self.session, {
                "rtmp": rtmp,
                "pageUrl": self.url,
                "swfUrl": SWF_URL,
                "playpath": playpath,
                "app": app,
            })
            streams[name] = stream

        return streams

    def _get_streams(self):
        res = http.get(self.url)

        match = _vod_id_re.search(res.text)
        if match:
            return self._get_vod_streams(match.group(1))

        match = _channel_id_re.search(res.text)
        if match:
            return self._get_live_streams(match.group(1))

__plugin__ = Filmon
