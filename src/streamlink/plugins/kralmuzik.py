from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class KralMuzik(Plugin):
    url_re = re.compile(r"https?://www.kralmuzik.com.tr/tv/kral-tv")
    stream_url_re = re.compile(r"(?P<quote>[\"'])(?P<url>https?://[^ ]*?/live/hls/[^ ]*?\?token=[^ ]*?)(?P=quote);")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        match = self.stream_url_re.search(res.text)
        if match:
            return HLSStream.parse_variant_playlist(self.session, match.group("url"))


__plugin__ = KralMuzik
