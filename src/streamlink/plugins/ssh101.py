import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.compat import urljoin


class SSH101(Plugin):
    url_re = re.compile(r"https?://(?:\w+\.)?ssh101\.com/(.+)(/vod)?")
    src_re = re.compile(r'''source.*?src="(?P<url>.*?)"''')
    iframe_re = re.compile(r'''iframe.*?src="(?P<url>.*?)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url)

    @Plugin.broken(1176)
    def _get_streams(self):
        res = http.get(self.url)

        # some pages have embedded players
        iframe_m = self.iframe_re.search(res.text)
        if iframe_m:
            url = urljoin(self.url, iframe_m.group("url"))
            res = http.get(url)

        video = self.src_re.search(res.text)
        stream_src = video and video.group("url")

        if stream_src and stream_src.endswith("m3u8"):
            return HLSStream.parse_variant_playlist(self.session, stream_src)


__plugin__ = SSH101
