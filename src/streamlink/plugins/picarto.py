import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import RTMPStream

API_CHANNEL_INFO = "https://picarto.tv/process/channel"
RTMP_URL = "rtmp://{}:1935/play/"
RTMP_PLAYPATH = "golive+{}?token={}"

_url_re = re.compile(r"""
    https?://(\w+\.)?picarto\.tv/[^&?/]
""", re.VERBOSE)

_channel_casing_re = re.compile(r"""
    <script>placeStreamChannel(Flash)?\('(?P<channel>[^']+)',[^,]+,[^,]+,'(?P<visibility>[^']+)'(,[^,]+)?\);</script>
""", re.VERBOSE)


class Picarto(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        page_res = http.get(self.url)
        match = _channel_casing_re.search(page_res.text)

        if not match:
            return {}

        channel = match.group("channel")
        visibility = match.group("visibility")

        channel_server_res = http.post(API_CHANNEL_INFO, data={
            "loadbalancinginfo": channel
        })

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": RTMP_URL.format(channel_server_res.text),
            "playpath": RTMP_PLAYPATH.format(channel, visibility),
            "pageUrl": self.url,
            "live": True
        })
        return streams

__plugin__ = Picarto
