"""
$description Vietnamese live TV channels from THVL, including THVL1, THVL2, THVL3 and THVL4.
$url thvli.vn
$type live
$region Vietnam
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?thvli\.vn/live/(?P<channel>[^/]+)'
))
class VinhLongTV(Plugin):
    api_url = 'http://api.thvli.vn/backend/cm/detail/{0}/'

    _data_schema = validate.Schema(
        {
            'link_play': validate.text,
        },
        validate.get('link_play')
    )

    def _get_streams(self):
        channel = self.match.group('channel')

        res = self.session.http.get(self.api_url.format(channel))
        hls_url = self.session.http.json(res, schema=self._data_schema)
        log.debug('URL={0}'.format(hls_url))

        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {'live': HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = VinhLongTV
