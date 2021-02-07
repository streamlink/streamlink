import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class TVToya(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?tvtoya\.pl/live")
    _playlist_re = re.compile(r'<source src="([^"]+)" type="application/x-mpegURL">')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.set_option('hls-live-edge', 10)
        res = self.session.http.get(self.url)
        playlist_m = self._playlist_re.search(res.text)

        if playlist_m:
            return HLSStream.parse_variant_playlist(self.session, playlist_m.group(1))
        else:
            log.debug("Could not find stream data")


__plugin__ = TVToya
