"""
$description Japanese Broadcast Satellite (BS) entertainment channel owned by Yoshimoto Kogyo Co. Ltd.
$url video.bsy.co.jp
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://video\.bsy\.co\.jp/?",
))
class BSYoshimoto(Plugin):
    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(re.compile(r"hls\.loadSource\(\s*(?P<q>[\"'])(?P<url>\S+)(?P=q)\s*\)").search),
            validate.none_or_all(
                validate.get("url"),
                validate.url(path=validate.endswith(".m3u8")),
            ),
        ))
        if not hls_url:
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = BSYoshimoto
