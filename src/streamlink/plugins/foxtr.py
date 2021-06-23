import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?fox(?:play)?\.com\.tr/"
))
class FoxTR(Plugin):
    playervars_re = re.compile(r"source\s*:\s*\[\s*\{\s*videoSrc\s*:\s*(?:mobilecheck\(\)\s*\?\s*)?'([^']+)'")

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self.playervars_re.search(res.text)
        if match:
            stream_url = match.group(1)
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = FoxTR
