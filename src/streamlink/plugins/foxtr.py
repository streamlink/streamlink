import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class FoxTR(Plugin):
    """
    Support for Turkish Fox live stream: http://www.fox.com.tr/canli-yayin
    """

    url_re = re.compile(r"""
        https?://(?:www.)?
        (?:fox.com.tr/.*|
           foxplay.com.tr/.*)
    """, re.VERBOSE)

    playervars_re = re.compile(r"source\s*:\s*\[\s*\{\s*videoSrc\s*:\s*(?:mobilecheck\(\)\s*\?\s*)?'([^']+)'")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self.playervars_re.search(res.text)
        if match:
            stream_url = match.group(1)
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = FoxTR
