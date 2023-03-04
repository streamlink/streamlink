"""
$description Turkish live TV channel owned by Hayat Visual Publishing Inc.
$url kanal7.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?kanal7\.com/canli-izle",
))
class Kanal7(Plugin):

    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""hls\s*:\s*(?P<q>["'])(?P<hls_url>https?://.*?\.m3u8.*?)(?P=q)"""),
            validate.any(None, validate.get("hls_url")),
        ))
        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Kanal7
