"""
$description Spanish live TV sports channel owned by Gol Network.
$url goltelevision.com
$type live
$region Spain
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?goltelevision\.com/en-directo"),
)
class GOLTelevision(Plugin):
    def _get_streams(self):
        self.session.http.headers.update({
            "Origin": "https://goltelevision.com",
            "Referer": "https://goltelevision.com/",
        })
        url = self.session.http.get(
            "https://play.goltelevision.com/api/stream/live",
            schema=validate.Schema(
                validate.parse_json(),
                {"manifest": validate.url()},
                validate.get("manifest"),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = GOLTelevision
