import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream

class LiveRussia(Plugin):
    url_re = re.compile(r"https?://(?:www.)?live.russia.tv/index/index/channel_id/")
    iframe_re = re.compile(r"""<iframe[^>]*src=["']([^'"]+)["'][^>]*>""")
    stream_re = re.compile(r"""window.pl.data.*m3u8":"(.*)"}.*};""")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        iframe_url = self.check_re(self.iframe_re, res.text)
        res = http.get(iframe_url)
        stream_url = self.check_re(self.stream_re, res.text)
        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def check_re(self, search, text):
        re_result = re.search(search, text)
        if re_result:
            return re_result.group(1)
        self.logger.error("The requested content is unavailable.")


__plugin__ = LiveRussia