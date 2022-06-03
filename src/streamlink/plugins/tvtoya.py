"""
$description Polish live TV channel owned by Toya.
$url tvtoya.pl
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tvtoya\.pl/player/live$"
))
class TVToya(Plugin):
    def _get_streams(self):
        self.session.set_option('hls-live-edge', 10)
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[@id='__NEXT_DATA__']/text()"),
            validate.parse_json(),
            {"props": {"pageProps": {"url": validate.all(
                validate.transform(lambda s: s.replace("//", "/")), validate.url(),
            )}}},
            validate.get(("props", "pageProps", "url")),
        ))
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TVToya
