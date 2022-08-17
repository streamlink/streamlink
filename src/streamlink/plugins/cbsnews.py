"""
$description 24-hour live-streaming world news channel, based in the United States of America.
$url cbsnews.com
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?cbsnews\.com/(?:\w+/)?live/?"
))
class CBSNews(Plugin):
    def _get_streams(self):
        data = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"CBSNEWS\.defaultPayload\s*=\s*(\{.*?})\s*\n"),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                {
                    "items": [{
                        "id": str,
                        "canonicalTitle": str,
                        "video": validate.url(),
                        "format": "application/x-mpegURL",
                    }],
                },
                validate.get(("items", 0)),
                validate.union_get("id", "canonicalTitle", "video"),
            ),
        ))
        if not data:
            return

        self.id, self.title, hls_url = data

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = CBSNews
