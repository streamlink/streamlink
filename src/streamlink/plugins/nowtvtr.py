"""
$description Turkish live TV channel owned by Disney.
$url nowtv.com.tr
$type live, vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?nowtv\.com\.tr/"),
)
class NowTVTR(Plugin):
    def _get_streams(self):
        stream_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"""(?P<q>['"])(?P<url>https://nowtv[^/]+/\S+/playlist\.m3u8\?\S+)(?P=q)"""),
                validate.none_or_all(validate.get("url")),
            ),
        )
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = NowTVTR
