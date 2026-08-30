"""
$description Live TV channels from RTVS, a Slovak public, state-owned broadcaster.
$url rtvs.sk
$type live
$region Slovakia
"""

import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://www\.rtvs\.sk/televizia/(?:live-|sport)"),
)
class Rtvs(Plugin):
    def _get_streams(self):
        channel = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//iframe[@id='player_live']//@src"),
                validate.url(path=validate.startswith("/embed/live/")),
                validate.transform(lambda embed: urlparse(embed).path[len("/embed/live/") :]),
            ),
        )
        if not channel:
            return

        videos = self.session.http.get(
            "https://www.rtvs.sk/json/live5f.json",
            params={
                "c": channel,
                "b": "mozilla",
                "p": "win",
                "f": "0",
                "d": "1",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "clip": {
                        "sources": [
                            {
                                "src": validate.url(),
                                "type": str,
                            },
                        ],
                    },
                },
                validate.get(("clip", "sources")),
                validate.filter(lambda n: n["type"] == "application/x-mpegurl"),
            ),
        )
        for video in videos:
            return HLSStream.parse_variant_playlist(self.session, video["src"])


__plugin__ = Rtvs
