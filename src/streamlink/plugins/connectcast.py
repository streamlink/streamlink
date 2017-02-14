import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

_url_re = re.compile(r"http(?:s)?://connectcast.tv/(\w+)?")
_stream_re = re.compile(r'file.*?:.*?"(.*?)"')


class ConnectCast(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = _stream_re.search(res.text)
        if match:
            streams = {}
            streams = HLSStream.parse_variant_playlist(self.session, match.group(1))
            self.logger.info("_get_stream")
            return streams


__plugin__ = ConnectCast
