"""
$description Turkish live TV channel owned by Detelina Media.
$url tv999.bg
$type live
$region Bulgaria
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?tv999\.bg/live"),
)
class TV999(Plugin):
    title = "TV999"

    def _get_xpath_string(self, url, xpath):
        return self.session.http.get(
            url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(xpath),
                validate.any(None, validate.url()),
            ),
        )

    def _get_streams(self):
        iframe_url = self._get_xpath_string(self.url, ".//iframe[@src]/@src")
        if not iframe_url:
            return
        hls_url = self._get_xpath_string(iframe_url, ".//source[contains(@src,'m3u8')]/@src")
        if not hls_url:
            return
        return {"live": HLSStream(self.session, update_scheme("http://", hls_url))}


__plugin__ = TV999
