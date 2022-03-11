"""
$description Turkish live TV channel owned by Fox Network.
$url fox.com.tr
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?fox(?:play)?\.com\.tr/"
))
class FoxTR(Plugin):
    def _get_streams(self):
        re_streams = re.compile(r"""(['"])(?P<url>https://\S+/foxtv\.m3u8\S+)\1""")
        res = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(re_streams.findall)
        ))
        for _, stream_url in res:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = FoxTR
