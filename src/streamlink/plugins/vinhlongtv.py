import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class VinhLongTV(Plugin):

    api_url = 'http://api.thvli.vn/backend/cm/detail/{0}/'

    _url_re = re.compile(
        r'https?://(?:www\.)?thvli\.vn/live/(?P<channel>[^/]+)')

    _data_schema = validate.Schema(
        {
            'link_play': validate.text,
        },
        validate.get('link_play')
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        http.headers.update({'User-Agent': useragents.FIREFOX})

        channel = self._url_re.match(self.url).group('channel')

        res = http.get(self.api_url.format(channel))
        hls_url = http.json(res, schema=self._data_schema)
        log.debug('URL={0}'.format(hls_url))

        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {'live': HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = VinhLongTV
