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
        iframe_result = re.search(self.iframe_re, res.text)

        if not iframe_result:
            self.logger.error("The requested content is unavailable.")
            return

        res = http.get(iframe_result.group(1))
        stream_url_result = re.search(self.stream_re, res.text)

        if not stream_url_result:
            self.logger.error("The requested content is unavailable.")
            return

        return HLSStream.parse_variant_playlist(self.session, stream_url_result.group(1))


__plugin__ = LiveRussia