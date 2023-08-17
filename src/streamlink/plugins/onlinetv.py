"""
$description Russian live-streaming platform for gaming and esports, owned by OnlineTV.
$url onlinetv.one
$type onlinetv
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://onlinetv\.one/video/(?P<channel_name>\w+)/?$",
))
class OnlineTV(Plugin):
    API_URL = "https://onlinetv.one/"

    def _get_streams(self):
        self.serial = self.match.group("channel_name")
        log.debug(f"Channel name: {self.serial}")

        data = self.session.http.get(
            f"{self.API_URL}/video/{self.serial}",
            headers={"Referer": self.url},
        )
        if type(data) is str:
            log.error(data)
            return

        self.category, self.title, streamdata = data
        if not streamdata:
            return

        self.id, streams = streamdata

        for streamtype, streamurl in streams:
            if streamurl and streamtype == "live_hls":
                return HLSStream.parse_variant_playlist(self.session, streamurl)


__plugin__ = OnlineTV
