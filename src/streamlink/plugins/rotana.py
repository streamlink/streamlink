"""
$description Saudi Arabian live TV channels from Rotana Media Group, including Classic, Clip, Comedy, Drama, Kids and LBC.
$url rotana.net
$type live
$region Saudi Arabia
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?rotana\.net/live'
))
class Rotana(Plugin):
    _hls_re = re.compile(r'''["'](?P<url>[^"']+\.m3u8)["']''')

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
