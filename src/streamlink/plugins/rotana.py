import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Rotana(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?rotana\.net/live')
    _hls_re = re.compile(r'''["'](?P<url>[^"']+\.m3u8)["']''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._hls_re.search(res.text)
        if not m:
            log.debug('No video URL found.')
            return

        hls_url = m.group('url')
        log.debug('URL={0}'.format(hls_url))
        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {'live': HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = Rotana
