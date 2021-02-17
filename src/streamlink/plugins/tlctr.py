import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class TLCtr(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?tlctv\.com\.tr/canli-izle')
    _token_params_re = re.compile(r'var liveUrl = ".*?tlctv(.*?)";')
    _api_url = 'https://dygvideo.dygdigital.com/live/hls/tlctvdai{0}&json=true'

    _api_schema = validate.Schema({
        'xtra': {
            'url': validate.url(),
        },
    }, validate.get('xtra'), validate.get('url'))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)

        m = self._token_params_re.search(res.text)
        if not m:
            log.error('Token data not found')
            return

        api_url = self._api_url.format(m.group(1))
        log.debug(f'API URL={api_url}')
        res = self.session.http.get(api_url)
        hls_url = self.session.http.json(res, schema=self._api_schema)
        log.debug(f'HLS URL={hls_url}')

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TLCtr
