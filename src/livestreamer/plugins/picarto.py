import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream

API_CHANNEL_INFO = "https://picarto.tv/process/channel"
RTMP_URL = "{}/?{}/{}"

_url_re = re.compile(r"""
    https?://(\w+\.)?picarto\.tv/[^&?/]
""", re.VERBOSE)

_channel_casing_re = re.compile(r"""
    <script>placeStreamChannel\('(?P<channel>[^']+)',[^,]+,[^,]+,'(?P<visibility>[^']+)'\);</script>
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
            "rtmp": RTMP_URL.format(channel_server_res.text, visibility, channel),
            "pageUrl": self.url,
            "live": True
        })
        return streams

__plugin__ = Picarto
