import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

API_URL = "https://live-api.line-apps.com/app/v3.2/channel/{0}/broadcast/{1}/player_status"

QUALITY_WEIGHTS = {
    "720": 720,
    "480": 480,
    "360": 360,
    "240": 240,
    "144": 144,
}

_url_re = re.compile(r"""
    https?://live.line.me
    /channels/(?P<channel>\d+)
    /broadcast/(?P<broadcast>\d+)
""", re.VERBOSE)

_player_status_schema = validate.Schema(
    {
        "liveStatus": validate.text,
        "liveHLSURLs": validate.any(None, {
            "720": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            "480": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            "360": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            "240": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            "144": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
        })
    }
)

class LineLive(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        weight = QUALITY_WEIGHTS.get(stream)
        if weight:
            return weight, "linelive"

        return Plugin.stream_weight(stream)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")
        broadcast = match.group("broadcast")
        res = self.session.http.get(API_URL.format(channel, broadcast))
        json = self.session.http.json(res, schema=_player_status_schema)
        if json["liveStatus"] != "LIVE":
            return
        for stream in json["liveHLSURLs"]:
            url = json["liveHLSURLs"][stream]
            if url != None:
                yield stream, HLSStream(self.session, url)


__plugin__ = LineLive
