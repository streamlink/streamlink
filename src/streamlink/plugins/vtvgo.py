import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class VTVgo(Plugin):

    AJAX_URL = 'https://vtvgo.vn/ajax-get-stream'

    _url_re = re.compile(r'https://vtvgo\.vn/xem-truc-tuyen-kenh-')
    _params_re = re.compile(r'''var\s(?P<key>(?:type_)?id|time|token)\s*=\s*["']?(?P<value>[^"']+)["']?;''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({
            'Origin': 'https://vtvgo.vn',
            'Referer': self.url,
            'User-Agent': useragents.FIREFOX,
            'X-Requested-With': 'XMLHttpRequest',
        })
        res = self.session.http.get(self.url)

        params = self._params_re.findall(res.text)
        if not params:
            raise PluginError('No POST data')
        elif len(params) != 4:
            raise PluginError('Not enough POST data: {0!r}'.format(params))

        log.trace('{0!r}'.format(params))
        res = self.session.http.post(self.AJAX_URL, data=dict(params))
        hls_url = self.session.http.json(res)['stream_url'][0]

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = VTVgo
