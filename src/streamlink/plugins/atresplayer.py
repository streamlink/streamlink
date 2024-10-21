"""
$description Spanish live TV channels from Atresmedia Television, including Antena 3 and laSexta.
$url atresplayer.com
$type live
$region Spain
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?atresplayer\.com/directos/.+"),
)
class AtresPlayer(Plugin):
    _channels_api_url = "https://api.atresplayer.com/client/v1/info/channels"
    _player_api_url = "https://api.atresplayer.com/player/v1/live/{channel_id}?NODRM=true"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = update_scheme("https://", f"{self.url.rstrip('/')}/")

    def _get_streams(self):
        channel_path = f"/{self.url.split('/')[-2]}/"
        channel_data = self.session.http.get(
            self._channels_api_url,
            schema=validate.Schema(
                validate.parse_json(),
                [
                    {
                        "id": str,
                        "link": {"url": str},
                    },
                ],
                validate.filter(lambda item: item["link"]["url"] == channel_path),
            ),
        )
        if not channel_data:
            return
        channel_id = channel_data[0]["id"]

        player_api_url = self._player_api_url.format(channel_id=channel_id)
        log.debug(f"Player API URL: {player_api_url}")

        sources = self.session.http.get(
            player_api_url,
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

        for streamtype, streamsrc in sources.get("sourcesLive"):
            log.debug(f"Stream source: {streamsrc} ({streamtype or 'n/a'})")

            if streamtype == "application/vnd.apple.mpegurl":
                streams = HLSStream.parse_variant_playlist(self.session, streamsrc)
                if not streams:
                    yield "live", HLSStream(self.session, streamsrc)
                else:
                    yield from streams.items()
            elif streamtype == "application/dash+xml":
                yield from DASHStream.parse_manifest(self.session, streamsrc).items()


__plugin__ = AtresPlayer
