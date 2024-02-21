"""
$description OTT video platform owned by Alpha Technology Group
$url media.gov.kw
$type live
"""

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    name="mangomoloplayer",
    pattern=re.compile(r"https?://player\.mangomolo\.com/v1/"),
)
@pluginmatcher(
    name="mediagovkw",
    pattern=re.compile(r"https?://media\.gov\.kw/"),
)
class Mangomolo(Plugin):
    def _get_player_url(self):
        player_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//iframe[contains(@src,'//player.mangomolo.com/v1/')][1]/@src"),
        ))
        if not player_url:
            log.error("Could not find embedded player")
            raise NoStreamsError

        self.url = update_scheme("https://", player_url)

    def _get_streams(self):
        if not self.matches["mangomoloplayer"]:
            self._get_player_url()

        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"src\s*:\s*(?P<q>[\"'])(?P<url>https?://\S+?\.m3u8\S*?)(?P=q)"),
            validate.none_or_all(validate.get("url")),
        ))
        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Mangomolo
