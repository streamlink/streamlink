"""
$description Live TV channels from LRT, a Lithuanian public, state-owned broadcaster.
$url lrt.lt
$type live
$metadata id
$metadata title
"""

import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.data import search_dict


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?lrt\.lt/mediateka/tiesiogiai/"),
)
class LRT(Plugin):
    def _get_streams(self):
        path = urlparse(self.url).path
        schema_get_live_url = validate.url(path=validate.endswith("/get_live_url.php"))
        channels = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'/get_live_url.php?channel=')][1]/text()"),
                validate.none_or_all(
                    validate.nextjs_inline_rsc(),
                    validate.transform(lambda d: next(search_dict(d, "channels"), None)),
                    validate.none_or_all(
                        [
                            {
                                "href": str,
                                "channel": str,
                                "title": str,
                                # keep `stream_url` as a fallback
                                validate.optional("stream_url"): schema_get_live_url,
                                validate.optional("get_streams_url"): schema_get_live_url,
                            },
                        ],
                    ),
                ),
            ),
        )
        for channel in channels:
            if channel["href"] == path:
                break
        else:
            return

        if not (get_live_url := channel.get("get_streams_url", channel.get("stream_url", ""))):
            return

        self.id = channel["channel"]
        self.title = channel["title"]

        hls_url = self.session.http.get(
            get_live_url,
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
