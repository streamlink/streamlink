import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

_url_re = re.compile(r"http(?:s)?://connectcast.tv/(\w+)?")
_stream_re = re.compile(r'<video src="mp4:(.*?)"')
_stream_url = "http://connectcast.tv/channel/stream/{channel}"


class ConnectCast(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        stream_url = _stream_url.format(channel=url_match.group(1))
        res = self.session.http.get(stream_url)
        match = _stream_re.search(res.text)
        if match:
            params = dict(rtmp="rtmp://stream.connectcast.tv/live",
                          playpath=match.group(1),
                          live=True)

            return dict(live=RTMPStream(self.session, params))


__plugin__ = ConnectCast
