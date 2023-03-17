"""
$description Russian live-streaming platform for gaming and esports, owned by VKontakte.
$url vkplay.live
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://vkplay\.live/(?P<channel_name>\w+)/?$",
))
class VKplay(Plugin):
    API_URL = "https://api.vkplay.live/v1"

    def _get_streams(self):
        self.author = self.match.group("channel_name")
        log.debug(f"Channel name: {self.author}")

        data = self.session.http.get(
            f"{self.API_URL}/blog/{self.author}/public_video_stream",
            headers={"Referer": self.url},
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"error": str, "error_description": str},
                        validate.get("error_description"),
                    ),
                    validate.all(
                        {
                            validate.optional("category"): validate.all(
                                {
                                    "title": str,
                                },
                                validate.get("title"),
                            ),
                            "title": str,
                            "data": validate.any(
                                [
                                    validate.all(
                                        {
                                            "vid": str,
                                            "playerUrls": [
                                                validate.all(
                                                    {
                                                        "type": str,
                                                        "url": validate.any("", validate.url()),
                                                    },
                                                    validate.union_get("type", "url"),
                                                ),
                                            ],
                                        },
                                        validate.union_get("vid", "playerUrls"),
                                    ),
                                ],
                                [],
                            ),
                        },
                        validate.union_get(
                            "category",
                            "title",
                            ("data", 0),
                        ),
                    ),
                ),
            ),
        )
        if type(data) is str:
            log.error(data)
            return

        self.category, self.title, streamdata = data
        if not streamdata:
            return

        self.id, streams = streamdata

        for streamtype, streamurl in streams:
            if streamurl and streamtype == "live_hls":
                return HLSStream.parse_variant_playlist(self.session, streamurl)


__plugin__ = VKplay
