import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

PAGE_URL = "https://www.tigerdile.com/stream/"
ROOT_URL = "rtmp://stream.tigerdile.com/live/{0}"
STREAM_TYPES = ["rtmp"]

_url_re = re.compile(r"""
    https?://(?:www|sfw)\.tigerdile\.com
    \/stream\/(.*)\/""", re.VERBOSE)


class Tigerdile(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = self.url
        streamname = _url_re.search(res).group(1)
        streams = {}
        stream = RTMPStream(self.session, {
            "rtmp": ROOT_URL.format(streamname),
            "pageUrl": PAGE_URL,
            "live": True,
            "app": "live",
            "flashVer": "LNX 11,2,202,280",
            "swfVfy": "https://www.tigerdile.com/wp-content/jwplayer.flash.swf",
            "playpath": streamname,
        })
        streams["live"] = stream

        return streams


__plugin__ = Tigerdile
