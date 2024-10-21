"""
$description French live TV channel and video on-demand service owned by Gulli.
$url replay.gulli.fr
$type live, vod
$region France
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://replay\.gulli\.fr/Direct"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://replay\.gulli\.fr/.+-(?P<video_id>(?i:vod)\d+)$"),
)
class Gulli(Plugin):
    LIVE_PLAYER_URL = "https://replay.gulli.fr/jwplayer/embedstreamtv"
    VOD_PLAYER_URL = "https://replay.gulli.fr/jwplayer/embed/{0}"

    def _get_streams(self):
        if self.matches["live"]:
            player_url = self.LIVE_PLAYER_URL
        else:
            player_url = self.VOD_PLAYER_URL.format(self.match["video_id"])

        video_url = self.session.http.get(
            player_url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//video-js[1]/source[@src][@type='application/x-mpegURL'][1]/@src"),
            ),
        )
        if not video_url:
            return

        return HLSStream.parse_variant_playlist(self.session, video_url)


__plugin__ = Gulli
