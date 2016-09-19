import re
from streamlink.plugin import Plugin
from streamlink.stream import RTMPStream, HTTPStream
from streamlink.plugin.api import http


_vod_re = re.compile('\"(http(s)?://.*\.mp4\?t=.*)\"')
_rtmp_re = re.compile('rtmp://[^"]+/(?P<channel>\w+)+[^/"]+')
_url_re = re.compile('http(s)?://(?:\w+.)?\livecoding\.tv')


class LivecodingTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _rtmp_re.search(res.content.decode('utf-8'))
        if match:
            params = {
                "rtmp": match.group(0),
                "pageUrl": self.url,
                "live": True,
            }
            yield 'live', RTMPStream(self.session, params)
            return

        match = _vod_re.search(res.content.decode('utf-8'))
        if match:
            yield 'vod', HTTPStream(self.session, match.group(1))

__plugin__ = LivecodingTV
