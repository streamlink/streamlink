from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class GalatasarayTV(Plugin):
    """
    Support for Galatasaray TV live stream: https://galatasaray.com/
    """

    url_re = re.compile(r"""
        https?://(?:www.)?
        (?:galatasaray.com/.*)
    """, re.VERBOSE)

    playervars_re = re.compile(r"sources\s*:\s*\[\s*\{\s*type\s*:\s*\"(.*?)\",\s*src\s*:\s*\"(.*?)\"", re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        print("url",url)
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self.playervars_re.search(res.text)
        if match:
            stream_url = match.group(2)
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = GalatasarayTV
