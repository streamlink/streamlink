import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class TVToya(Plugin):
    _url_re = re.compile(r"https?://tvtoya.pl/live")
    _playlist_re = re.compile(r'data-stream="([^"]+)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.set_option('hls-live-edge', 10)
        res = self.session.http.get(self.url)
        playlist_m = self._playlist_re.search(res.text)

        if playlist_m:
            return HLSStream.parse_variant_playlist(
                self.session,
                update_scheme(self.url, playlist_m.group(1)),
                headers={'Referer': self.url, 'User-Agent': useragents.ANDROID}
            )
        else:
            log.debug("Could not find stream data")


__plugin__ = TVToya
