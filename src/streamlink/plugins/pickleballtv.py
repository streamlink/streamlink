"""
$description pickleballtv.com
$url pickleballtv.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    pattern=re.compile(r"https?://pickleballtv\.com"),
)
class PickleballTV(Plugin):

    def _get_streams(self):

        playlist = self.session.http.get(
            "https://cdn.jwplayer.com/v2/media/kqrvUq1X",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "playlist": [
                        {
                            "sources": [
                                {
                                    "file": validate.url(
                                        path=validate.endswith(".m3u8"),
                                    ),
                                },
                            ],
                        },
                    ],
                },
                # Wasn't able to traverse down to "file" element
                # Just validate to the playlist element
                validate.get("playlist"),
            ),
        )
        log.debug(f"playlist: {playlist}")

        try:
            video_url = playlist[0]["sources"][0]["file"]
        except Exception:
            log.exception("Failed to extract video URL")

        if not video_url:
            log.warn("Could not find video URL")
            return

        log.info(f"Using video URL: {video_url}")

        return HLSStream.parse_variant_playlist(self.session, video_url)


__plugin__ = PickleballTV
