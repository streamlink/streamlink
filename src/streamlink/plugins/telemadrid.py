"""
$description Spanish live TV channel for Telemadrid, a public regional television station.
$url telemadrid.es
$type live, vod
$region Spain
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugins.brightcove import BrightcovePlayer


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?telemadrid\.es/"),
)
class Telemadrid(Plugin):
    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//video-js[@data-video-id][@data-account][@data-player][1]"),
                validate.union_get("data-video-id", "data-account", "data-player"),
            ),
        )
        data_video_id, data_account, data_player = data
        player = BrightcovePlayer(self.session, data_account, f"{data_player}_default")
        return player.get_streams(data_video_id)


__plugin__ = Telemadrid
