"""
$description Turkish live TV channel owned by Discovery, Inc.
$url tlctv.com.tr
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?tlctv\.com\.tr/canli-izle'
))
class TLCtr(Plugin):
    _hls_re = re.compile(
        r'''["'](?P<url>https?://[^/]+/live/hls/[^"']+)["']''')

    def _get_streams(self):
        res = self.session.http.get(self.url)

        m = self._hls_re.search(res.text)
        if not m:
            log.error('No playlist found.')
            return

        hls_url = m.group('url')
        log.debug('URL={0}'.format(hls_url))
        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {'live': HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = TLCtr
