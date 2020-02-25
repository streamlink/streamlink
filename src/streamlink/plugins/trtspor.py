from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream


class TRTSpor(Plugin):
    """
    Support for trtsport.com a Turkish Sports Broadcaster
    """
    url_re = re.compile(r"https?://(?:www.)?trtspor.com/canli-yayin-izle/.+/?")
    f4mm_re = re.compile(r'''(?P<q>["'])(?P<url>http[^"']+?.f4m)(?P=q),''')
    m3u8_re = re.compile(r'''(?P<q>["'])(?P<url>http[^"']+?.m3u8)(?P=q),''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        url_m = self.m3u8_re.search(res.text)
        hls_url = url_m and url_m.group("url")
        if hls_url:
            for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                yield s

        f4m_m = self.f4mm_re.search(res.text)
        f4m_url = f4m_m and f4m_m.group("url")
        if f4m_url:
            for n, s in HDSStream.parse_manifest(self.session, f4m_url).items():
                yield n, s


__plugin__ = TRTSpor
