import re

from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.plugin.api import http


_rtmp_re = re.compile('rtmp://[^"]+/(?P<channel>\w+)+[^/"]+')
_url_re = re.compile("http(s)?://(?:\w+.)?\livecoding\.tv")


class LivecodingTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _rtmp_re.search(res.text)
        rtmp_url = match.group(0)

        if not match:
            return

        stream = RTMPStream(self.session, {
            "rtmp": rtmp_url,
            "pageUrl": self.url,
            "live": True,
        })

        return dict(live=stream)


__plugin__ = LivecodingTV
