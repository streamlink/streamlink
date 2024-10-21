"""
$description Live TV channels from LRT, a Lithuanian public, state-owned broadcaster.
$url lrt.lt
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?lrt\.lt/mediateka/tiesiogiai/"),
)
class LRT(Plugin):
    def _get_streams(self):
        token_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"""var\s+tokenURL\s*=\s*(?P<q>["'])(?P<url>https://\S+)(?P=q)"""),
                validate.none_or_all(validate.get("url")),
            ),
        )
        if not token_url:
            return

        hls_url = self.session.http.get(
            token_url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "response": {
                        "data": {
                            "content": validate.all(
                                str,
                                validate.transform(lambda url: url.strip()),
                                validate.url(path=validate.endswith(".m3u8")),
                            ),
                        },
                    },
                },
                validate.get(("response", "data", "content")),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = LRT
