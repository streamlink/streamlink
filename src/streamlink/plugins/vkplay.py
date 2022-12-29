"""
$description Russian live-streaming platform.
$url vkplay.live
$type live
"""

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://vkplay\.live/(?P<channel_name>[a-zA-Z0-9_]+)/?$"
))
class VKplay(Plugin):
    API_URL = "https://api.vkplay.live/v1"

    def _get_streams(self):
        channel_name = self.match.group("channel_name")
        if not channel_name:
            return

        log.debug(f"Channel name: {channel_name}")
        try:
            res = self.session.http.get(
                f"{self.API_URL}/blog/{channel_name}/public_video_stream",
                headers={"Referer": self.url},
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "data":
                            [{
                                "playerUrls": validate.all(
                                    [{
                                        "url": validate.any(validate.url(), ""),
                                        "type": validate.any("live_hls", validate.text)
                                    }],
                                    validate.filter(lambda item: item["type"] == "live_hls")),

                            }]

                    }, validate.get("data"), validate.get(0), validate.get("playerUrls"), validate.get(0), validate.get("url"))
            )
        except PluginError:
            raise NoStreamsError(self.url)
        yield from HLSStream.parse_variant_playlist(self.session, res).items()


__plugin__ = VKplay
