"""
$description A privately owned Bulgarian live TV channel.
$url btvplus.bg
$type live
$region Bulgaria
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?btvplus\.bg/live/?"),
)
class BTV(Plugin):
    _URL_TOKEN = "https://dai-api.bweb.bg:3000/get-token"
    _URL_LIVESESSIONS = "https://videostitcher.googleapis.com/v1/projects/{project}/locations/{region}/liveSessions"
    _URL_STREAM_ID = "https://pubads.g.doubleclick.net/ssai/pods/api/v1/network/{network}/custom_asset/{asset_key}/stream"

    def _get_streams(self):
        access_token = self.session.http.get(
            self._URL_TOKEN,
            schema=validate.Schema(
                validate.parse_json(),
                {"access_token": str},
                validate.get("access_token"),
            ),
        )

        event_id, asset_key, region, project, network = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'streamData')][1]/text()"),
                str,
                validate.regex(re.compile(r"streamData\s*:\s*(\{.+?}),", re.DOTALL)),
                validate.get(1),
                validate.union(
                    tuple(
                        validate.all(
                            validate.regex(re.compile(rf"""{key}\s*:\s*(?P<q>['"])(?P<value>.+?)(?P=q)""")),
                            validate.get("value"),
                        )
                        for key in ("eventId", "assetKey", "region", "project", "network")
                    ),
                ),
            ),
        )
        log.debug(f"{event_id=} {asset_key=} {region=} {project=} {network=}")

        # apparently, we don't need POST data
        stream_id = self.session.http.post(
            self._URL_STREAM_ID.format(network=network, asset_key=asset_key),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "stream_id": str,
                },
                validate.get("stream_id"),
            ),
        )

        stream_url = self.session.http.post(
            self._URL_LIVESESSIONS.format(project=project, region=region),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "live_config": f"projects/{project}/locations/{region}/liveConfigs/{event_id}",
                "gam_settings": {
                    "stream_id": stream_id,
                },
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "playUri": validate.url(path=validate.endswith(".m3u8")),
                },
                validate.get("playUri"),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = BTV
