"""
$description Global live streaming platform.
$url ssh101.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?ssh101\.com/(?:(?:secure)?live/|detail\.php\?id=\w+)",
))
class SSH101(Plugin):
    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//source[contains(@src,'.m3u8')]/@src"),
        ))
        if not hls_url:
            return

        res = self.session.http.get(hls_url, acceptable_status=(200, 403, 404))
        if res.status_code != 200 or len(res.text) <= 10:
            log.error("This stream is currently offline")
            return

        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = SSH101
