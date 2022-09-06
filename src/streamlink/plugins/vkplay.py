"""
$description Russian live-streaming platform owned by VK Company Limited.
$url vkplay.live
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://vkplay.live/(?P<channel>[^/]+)"))
class VKPlay(Plugin):
    API_URL = "https://api.vkplay.live/v1/blog/{0}/public_video_stream"

    def _get_streams(self):
        data = self.session.http.get(
            self.API_URL.format(self.match.group("channel")),
            acceptable_status=(200, 400, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "error": str,
                        "error_description": str,
                    },
                    {
                        "daNick": str,
                        "title": str,
                        validate.optional("category"): validate.all(
                            {
                                "title": str
                            },
                            validate.get("title"),
                        ),
                        "data": validate.none_or_all(
                            [dict],
                            validate.get(0),
                            validate.none_or_all(
                                {
                                    "vid": str,
                                    "playerUrls": validate.all(
                                        [dict],
                                        validate.filter(lambda u: u.get("url") and "playback" not in u.get("type")),
                                        [
                                            {
                                                "type": str,
                                                "url": validate.url(),
                                            },
                                        ],
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
        )

        log.trace(data)

        error = data.get("error")
        if error:
            desc = data.get("error_description")
            log.error(f"Error: {error!r}, desc: {desc!r}")
            return

        stream = data.get("data")
        if not stream:
            log.error("Stream is currently offline.")
            return

        self.id = stream.get("vid")
        self.title = data.get("title")
        self.author = data.get("daNick")
        self.category = data.get("category")

        for playlist in stream.get("playerUrls"):
            url = playlist.get("url")
            kind = playlist.get("type")
            if kind.endswith("hls"):
                return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = VKPlay
