"""
$description Spanish live TV for DMAX broadcasted by Marca.
$url dmax.marca.com
$type live
$region Spain
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:dmax\.)?marca\.com/en-directo"),
)
class DmaxSpain(Plugin):
    _channel_api_url = (
        "https://public.aurora.enhanced.live/site/page/en-directo/?include=default&filter[environment]=dmaxspain&v=2"
    )
    _player_api_url = "https://public.aurora.enhanced.live/playback/channelPlaybackInfo/1?usePreAuth=true"

    def _get_streams(self):
        channel_data = self.session.http.get(
            self._channel_api_url,
            schema=validate.Schema(
                validate.parse_json(),
            ),
        )
        if not channel_data:
            return
        channel_auth = channel_data["userMeta"]["realm"]["X-REALM-ES"]

        headers = {
            "Authorization": f"Bearer {channel_auth}",
        }

        sources = self.session.http.get(
            self._player_api_url,
            acceptable_status=(200, 403),
            headers=headers,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "code": str,
                        "detail": str,
                    },
                    {
                        "streaming": [
                            validate.all(
                                {
                                    "url": validate.url(),
                                    "type": str,
                                },
                                validate.union_get("type", "src"),
                            ),
                        ],
                    },
                ),
            ),
        )

        if "errors" in sources:
            log.error(f"Stream error: {sources['errors'][0]['code']} - {sources['errors'][0]['detail']}")
            return

        for streamtype, streamsrc in sources.get("streaming"):
            log.debug(f"Stream source: {streamsrc} ({streamtype or 'n/a'})")

            if streamtype == "hls":
                streams = HLSStream.parse_variant_playlist(self.session, streamsrc)
                if not streams:
                    yield "live", HLSStream(self.session, streamsrc)
                else:
                    yield from streams.items()
            elif streamtype == "dash":
                yield from DASHStream.parse_manifest(self.session, streamsrc).items()


__plugin__ = DmaxSpain
