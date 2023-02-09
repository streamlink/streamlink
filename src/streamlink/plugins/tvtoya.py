"""
$description Polish live TV channel owned by Toya.
$url tvtoya.pl
$type live
"""

import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tvtoya\.pl/player/live",
))
class TVToya(Plugin):
    def _get_streams(self):
        try:
            hls = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[@type='application/json'][@id='__NEXT_DATA__']/text()"),
                str,
                validate.parse_json(),
                {
                    "props": {
                        "pageProps": {
                            "type": "live",
                            "url": validate.all(
                                str,
                                validate.transform(lambda url: url.replace("https:////", "https://")),
                                validate.url(path=validate.endswith(".m3u8")),
                            ),
                        },
                    },
                },
                validate.get(("props", "pageProps", "url")),
            ))
        except PluginError:
            return

        return HLSStream.parse_variant_playlist(self.session, hls)


__plugin__ = TVToya
