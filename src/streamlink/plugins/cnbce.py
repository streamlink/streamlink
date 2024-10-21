"""
$description Turkish live TV channel owned by NBCUniversal Media.
$url cnbce.com
$type live
$region Turkey
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?cnbce\.com/canli-yayin"))
class CNBCE(Plugin):
    _URL_API = "https://www.cnbce.com/api/live-stream/source"

    def _get_streams(self):
        hls_url = self.session.http.post(
            self._URL_API,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "source": validate.url(path=validate.endswith(".m3u8")),
                },
                validate.get("source"),
            ),
        )
        if self.session.http.get(hls_url, raise_for_status=False).status_code != 200:
            log.error("Could not access stream (geo-blocked content, etc.)")
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = CNBCE
