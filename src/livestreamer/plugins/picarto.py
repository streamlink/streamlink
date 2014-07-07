import re

from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream

RTMP_URL = "rtmp://live.us.picarto.tv/golive/{0}"

_url_re = re.compile("""
    http(s)?://(\w+\.)?picarto.tv
    /live/channel.php
    .+watch=(?P<channel>[^&?/]+)
""", re.VERBOSE)


class Picarto(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": RTMP_URL.format(channel),
            "pageUrl": self.url,
            "live": True
        })
        return streams

__plugin__ = Picarto
