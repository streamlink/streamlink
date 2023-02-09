"""
$description Russian live TV channel owned by Gazprom Media.
$url ntv.ru
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://www\.ntv\.ru/air/",
))
class NTV(Plugin):
    def _get_streams(self):
        body = self.session.http.get(self.url).text
        mrl = None
        match = re.search(r"var camHlsURL = \'(.*)\'", body)
        if match:
            mrl = f"http:{match.group(1)}"
        else:
            match = re.search(r"var hlsURL = \'(.*)\'", body)
            if match:
                mrl = match.group(1)
        if mrl:
            return HLSStream.parse_variant_playlist(self.session, mrl)


__plugin__ = NTV
