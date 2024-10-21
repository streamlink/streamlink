"""
$description Global live-streaming platform for live video game broadcasts and individual live streams.
$url bigo.tv
$type live
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?bigo\.tv/(?P<site_id>[^/]+)$"),
)
class Bigo(Plugin):
    _URL_API = "https://ta.bigo.tv/official_website/studio/getInternalStudioInfo"

    def _get_streams(self):
        self.id, self.author, self.category, self.title, hls_url = self.session.http.post(
            self._URL_API,
            params={
                "siteId": self.match["site_id"],
                "verify": "",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "roomId": validate.any(None, str),
                        "clientBigoId": validate.any(None, str),
                        "gameTitle": str,
                        "roomTopic": str,
                        "hls_src": validate.any(None, "", validate.url()),
                    },
                },
                validate.union_get(
                    ("data", "roomId"),
                    ("data", "clientBigoId"),
                    ("data", "gameTitle"),
                    ("data", "roomTopic"),
                    ("data", "hls_src"),
                ),
            ),
        )

        if not self.id:
            return

        if not hls_url:
            log.info("Channel is offline")
            return

        yield "live", HLSStream(self.session, hls_url)


__plugin__ = Bigo
