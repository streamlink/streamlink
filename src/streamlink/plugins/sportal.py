"""
$description Sporting channel live stream owned by Sportal, a Bulgarian sports media website.
$url sportal.bg
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?sportal\.bg/sportal_live_tv\.php"),
)
class Sportal(Plugin):
    _hls_re = re.compile(r"""["'](?P<url>[^"']+\.m3u8[^"']*?)["']""")

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._hls_re.search(res.text)
        if not m:
            return

        hls_url = m.group("url")
        log.debug("URL={0}".format(hls_url))
        log.warning("SSL certificate verification is disabled.")
        return HLSStream.parse_variant_playlist(self.session, hls_url, verify=False).items()


__plugin__ = Sportal
