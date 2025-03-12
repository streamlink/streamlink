"""
$description Live TV channels and video on-demand service from NOS, a Dutch public, state-owned broadcaster.
$url nos.nl
$type live, vod
$metadata id
$metadata title
$region Netherlands
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:\w+\.)?nos\.nl/(?:live$|livestream/|l/|video/|collectie/)"),
)
class NOS(Plugin):
    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[@type='application/ld+json'][1]/text()"),
                validate.none_or_all(
                    validate.parse_json(),
                    {
                        "@type": validate.any(
                            "VideoObject",
                            validate.all(
                                list,
                                validate.contains("VideoObject"),
                            ),
                        ),
                        "encodingFormat": "application/vnd.apple.mpegurl",
                        "contentUrl": validate.url(),
                        "identifier": validate.any(int, str),
                        "name": str,
                    },
                    validate.union_get(
                        "contentUrl",
                        "identifier",
                        "name",
                    ),
                ),
            ),
        )
        if not data:
            return

        hls_url, self.id, self.title = data

        res = self.session.http.get(hls_url, raise_for_status=False)
        if res.status_code >= 400:
            log.error("Content is inaccessible or may have expired")
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = NOS
