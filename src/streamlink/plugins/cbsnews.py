"""
$description 24-hour live streaming world news channel, based in the United States of America.
$url cbsnews.com
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://www\.cbsnews\.com/live/"
))
class CBSNews(Plugin):
    def _get_streams(self):
        items = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"CBSNEWS.defaultPayload = (\{.*)"),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                {
                    "items": [
                        validate.all(
                            {
                                "video": validate.url(),
                                "format": "application/x-mpegURL",
                            },
                            validate.get("video"),
                        ),
                    ],
                },
                validate.get("items"),
            ),
        ))
        if items:
            for hls_url in items:
                yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = CBSNews
