import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tvtoya\.pl/live"
))
class TVToya(Plugin):
    _playlist_re = re.compile(r'<source src="([^"]+)" type="application/x-mpegURL">')

    def _get_streams(self):
        self.session.set_option('hls-live-edge', 10)
        res = self.session.http.get(self.url)
        playlist_m = self._playlist_re.search(res.text)

        if playlist_m:
            return HLSStream.parse_variant_playlist(self.session, playlist_m.group(1))
        else:
            log.debug("Could not find stream data")


__plugin__ = TVToya
