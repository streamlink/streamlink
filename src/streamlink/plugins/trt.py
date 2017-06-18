from __future__ import print_function
import re
from base64 import b64decode

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.compat import urlparse, parse_qsl
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream


class TRT(Plugin):
    """
    Support for the live TV streams on http://www.trt.net.tr/, some streams may be geo-locked
    """
    url_re = re.compile(r"http://www.trt.net.tr/anasayfa/canli.aspx.*", re.I)
    stream_data_re = re.compile(r'<script>eval\(dcm1\("(.*?)"\)\);')
    f4mm_re = re.compile(r'''(?P<q>["'])(?P<url>http[^"']+?.f4m)(?P=q);''')
    m3u8_re = re.compile(r'''(?P<q>["'])(?P<url>http[^"']+?.m3u8)(?P=q);''')

    @classmethod
    def can_handle_url(cls, url):
        if cls.url_re.match(url) is not None:
            args = dict(parse_qsl(urlparse(url).query))
            return args.get("y") == "tv"

    def _get_streams(self):
        args = dict(parse_qsl(urlparse(self.url).query))
        if "k" in args:
            self.logger.debug("Loading channel: {k}", **args)
            res = http.get(self.url)
            stream_data_m = self.stream_data_re.search(res.text)
            if stream_data_m:
                script_vars = b64decode(stream_data_m.group(1)).decode("utf8")
                url_m = self.m3u8_re.search(script_vars)

                hls_url = url_m and url_m.group("url")
                if hls_url:
                    for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                        yield s

                f4m_m = self.f4mm_re.search(script_vars)
                f4m_url = f4m_m and f4m_m.group("url")
                if f4m_url:
                    for n, s in HDSStream.parse_manifest(self.session, f4m_url).items():
                        yield n, s


__plugin__ = TRT
