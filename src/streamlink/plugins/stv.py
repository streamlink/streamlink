"""
$description Live TV channels from STV, a Scottish free-to-air broadcaster.
$url player.stv.tv
$type live
$region United Kingdom
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://player\.stv\.tv/live",
))
class STV(Plugin):
    API_URL = "https://player.api.stv.tv/v1/streams/stv/"

    def get_title(self):
        if self.title is None:
            self._get_api_results()
        return self.title

    def _get_api_results(self):
        res = self.session.http.get(self.API_URL)
        data = self.session.http.json(res)

        if data["success"] is False:
            raise PluginError(data["reason"]["message"])

        try:
            self.title = data["results"]["now"]["title"]
        except KeyError:
            self.title = "STV"

        return data

    def _get_streams(self):
        hls_url = self._get_api_results()["results"]["streamUrl"]
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = STV
