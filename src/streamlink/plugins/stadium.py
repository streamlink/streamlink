"""
$description Sporting live stream and video content, owned by Silver Chalice and Sinclair Broadcast Group.
$url watchstadium.com
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?watchstadium\.com/"),
)
class Stadium(Plugin):
    _API_URL = "https://edge.api.brightcove.com/playback/v1/accounts/{data_account}/videos/{data_video_id}"
    _PLAYER_URL = "https://players.brightcove.net/{data_account}/{data_player}_default/index.min.js"

    def _get_streams(self):
        try:
            data = self.session.http.get(
                self.url,
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_find(".//video[@id='brightcove_video_player']"),
                    validate.union_get("data-video-id", "data-account", "data-ad-config-id", "data-player"),
                ),
            )
        except PluginError:
            return
        data_video_id, data_account, data_ad_config_id, data_player = data

        url = self._PLAYER_URL.format(data_account=data_account, data_player=data_player)
        policy_key = self.session.http.get(
            url,
            schema=validate.Schema(
                re.compile(r"""options:\s*{.+policyKey:\s*"([^"]+)""", re.DOTALL),
                validate.any(None, validate.get(1)),
            ),
        )
        if not policy_key:
            return

        url = self._API_URL.format(data_account=data_account, data_video_id=data_video_id)
        if data_ad_config_id is not None:
            url = update_qsd(url, dict(ad_config_id=data_ad_config_id))

        streams = self.session.http.get(
            url,
            headers={"Accept": f"application/json;pk={policy_key}"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "sources": [
                        {
                            validate.optional("type"): str,
                            "src": validate.url(),
                        },
                    ],
                },
                validate.get("sources"),
                validate.filter(lambda source: source.get("type") == "application/x-mpegURL"),
            ),
        )

        for stream in streams:
            return HLSStream.parse_variant_playlist(self.session, stream["src"])


__plugin__ = Stadium
