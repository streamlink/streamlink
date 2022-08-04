"""
$description Turkish live TV channel owned by Acun Medya Group.
$url tv8.com.tr
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://www\.tv8\.com\.tr/canli-yayin"
))
class TV8(Plugin):
    title = "TV8"

    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""file\s*:\s*(?P<q>["'])(?P<hls_url>https?://.*?\.m3u8.*?)(?P=q)"""),
            validate.any(None, validate.get("hls_url")),
        ))
        if hls_url is not None:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TV8
