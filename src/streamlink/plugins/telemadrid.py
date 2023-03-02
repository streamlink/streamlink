"""
$description Spanish live TV channel for Telemadrid
$url telemadrid.es
$type live, vod
$region Spain
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?telemadrid\.es/",
))
class Telemadrid(Plugin):
    _API_URL = "https://edge.api.brightcove.com/playback/v1/accounts/{data_account}/videos/{data_video_id}"
    _PLAYER_URL = "https://players.brightcove.net/{data_account}/{data_player}_default/index.min.js"

    def _get_streams(self):
        try:
            data = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//video[@class='video-js']"),
                validate.union_get("data-video-id", "data-account", "data-player"),
            ))
        except PluginError:
            return
        data_video_id, data_account, data_player = data

        url = self._PLAYER_URL.format(data_account=data_account, data_player=data_player)
        policy_key = self.session.http.get(url, schema=validate.Schema(
            re.compile(r"""options:\s*{.+policyKey:\s*"([^"]+)""", re.DOTALL),
            validate.any(None, validate.get(1)),
        ))
        if not policy_key:
            return

        url = self._API_URL.format(data_account=data_account, data_video_id=data_video_id)

        streams = self.session.http.get(
            url,
            headers={"Accept": f"application/json;pk={policy_key}"},
            schema=validate.Schema(
                validate.parse_json(),
                validate.get("sources"),
            ),
        )

        for stream in streams:
            return HLSStream.parse_variant_playlist(self.session, stream["src"])


__plugin__ = Telemadrid
