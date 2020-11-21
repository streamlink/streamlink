import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Sportal(Plugin):

    _url_re = re.compile(
        r'https?://(?:www\.)?sportal\.bg/sportal_live_tv.php.*')
    _hls_re = re.compile(r'''["'](?P<url>[^"']+\.m3u8[^"']*?)["']''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._hls_re.search(res.text)
        if not m:
            return

        hls_url = m.group('url')
        log.debug('URL={0}'.format(hls_url))
        log.warning('SSL certificate verification is disabled.')
        return HLSStream.parse_variant_playlist(
            self.session, hls_url, verify=False).items()


__plugin__ = Sportal
