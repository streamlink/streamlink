"""
$description Spanish live TV channels from Atresmedia Television, including Antena 3 and laSexta.
$url atresplayer.com
$type live
$region Spain
"""

import re
from urllib.parse import urlparse

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?atresplayer\.com/directos/.+"),
)
class AtresPlayer(Plugin):
    _live_api_url = "https://api.atresplayer.com/client/v1/row/live"
    _stream_priorities = {
        "application/hls+legacy": 0,
        "application/vnd.apple.mpegurl": 1,
        "application/dash+xml": 2,
        "application/hls+hevc": 3,
        "application/dash+hevc": 4,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = update_scheme("https://", f"{self.url.rstrip('/')}/")

    def _get_streams(self):
        channel_path = urlparse(self.url).path

        log.debug(f"Channel path: {channel_path}")

        channels = self.session.http.get(
            self._live_api_url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "itemRows": [
                        {
                            "link": {
                                "url": str,
                                "href": validate.url(),
                            },
                        },
                    ],
                },
                validate.get("itemRows"),
            ),
        )

        channel = next(
            (item for item in channels if item["link"]["url"] == channel_path),
            None,
        )

        if not channel:
            log.error(f"Could not find live channel: {channel_path}")
            return

        page_api_url = channel["link"]["href"]

        log.debug(f"Page API URL: {page_api_url}")

        video_api_url = self.session.http.get(
            page_api_url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "urlVideo": validate.url(),
                },
                validate.get("urlVideo"),
            ),
        )

        log.debug(f"Video API URL: {video_api_url}")

        sources = self.session.http.get(
            video_api_url,
            acceptable_status=(200, 403),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "error": str,
                        "error_description": str,
                    },
                    {
                        "sourcesLive": [
                            validate.all(
                                {
                                    "src": validate.url(),
                                    validate.optional("type"): str,
                                },
                                validate.union_get("type", "src"),
                            ),
                        ],
                    },
                ),
            ),
        )

        if "error" in sources:
            log.error(f"Player API error: {sources['error']} - {sources['error_description']}")
            return

        for streamtype, streamsrc in sorted(
            sources.get("sourcesLive", []),
            key=lambda source: self._stream_priorities.get(source[0], -1),
            reverse=True,
        ):
            log.debug(f"Stream source: {streamsrc} ({streamtype or 'n/a'})")

            if streamtype in (
                "application/vnd.apple.mpegurl",
                "application/hls+legacy",
                "application/hls+hevc",
            ):
                streams = HLSStream.parse_variant_playlist(
                    self.session,
                    streamsrc,
                )

                if not streams:
                    yield "live", HLSStream(self.session, streamsrc)
                else:
                    yield from streams.items()

                return

            elif streamtype in (
                "application/dash+xml",
                "application/dash+hevc",
            ):
                streams = DASHStream.parse_manifest(
                    self.session,
                    streamsrc,
                )

                if streams:
                    yield from streams.items()
                    return


__plugin__ = AtresPlayer
