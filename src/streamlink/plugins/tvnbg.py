import re

from streamlink.plugin import Plugin
from streamlink.compat import urljoin
from streamlink.stream import HLSStream


class TVNBG(Plugin):
    url_re = re.compile(r"https?://(?:live\.)?tvn\.bg/(?:live)?")
    iframe_re = re.compile(r'<iframe.*?src="([^"]+)".*?></iframe>')
    src_re = re.compile(r'<source.*?src="([^"]+)".*?/>')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        base_url = self.url
        res = self.session.http.get(self.url)

        # Search for the iframe in the page
        iframe_m = self.iframe_re.search(res.text)
        if iframe_m:
            # If the iframe is found, load the embedded page
            base_url = iframe_m.group(1)
            res = self.session.http.get(iframe_m.group(1))

        # Search the page (original or embedded) for the stream URL
        src_m = self.src_re.search(res.text)
        if src_m:
            stream_url = urljoin(base_url, src_m.group(1))
            # There is no variant playlist, only a plain HLS Stream
            yield "live", HLSStream(self.session, stream_url)


__plugin__ = TVNBG
