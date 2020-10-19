import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class SSH101(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?ssh101\.com/(?:secure)?live/')
    src_re = re.compile(r'sources.*?src:\s"(?P<url>.*?)"')
    iframe_re = re.compile(r'iframe.*?src="(?P<url>.*?)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url)

    def _get_streams(self):
        res = self.session.http.get(self.url)

        # some pages have embedded players
        iframe_m = self.iframe_re.search(res.text)
        if iframe_m:
            url = urljoin(self.url, iframe_m.group("url"))
            res = self.session.http.get(url)

        video = self.src_re.search(res.text)
        stream_src = video and video.group("url")

        if stream_src and stream_src.endswith("m3u8"):
            # do not open empty m3u8 files
            if len(self.session.http.get(stream_src).text) <= 10:
                log.error("This stream is currently offline")
                return

            log.debug("URL={0}".format(stream_src))
            streams = HLSStream.parse_variant_playlist(self.session, stream_src)
            if not streams:
                return {"live": HLSStream(self.session, stream_src)}
            else:
                return streams


__plugin__ = SSH101
