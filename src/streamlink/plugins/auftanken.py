"""
$url auftanken.tv
$type live
$notes VOD streams are hosted on youtube
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?auftanken\.tv/livestream/?"
))
class AuftankenTV(Plugin):
    _hls_url_re = re.compile(r"(https://.+?/http_adaptive_streaming/\w+\.m3u8)")

    PLAYER_URL = "https://webplayer.sbctv.ch/auftanken/"

    def get_title(self):
        return "auftanken.TV Livestream"

    def _get_streams(self):
        res = self.session.http.get(self.PLAYER_URL)
        m = self._hls_url_re.search(res.text)
        if m:
            for s in HLSStream.parse_variant_playlist(self.session, m.group(1)).items():
                yield s


__plugin__ = AuftankenTV
