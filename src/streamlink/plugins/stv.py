import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class STV(Plugin):
    _url_re = re.compile(r'https?://player\.stv\.tv/live')

    API_URL = 'https://player.api.stv.tv/v1/streams/stv/'

    title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def get_title(self):
        if self.title is None:
            self._get_api_results()
        return self.title

    def _get_api_results(self):
        self.session.http.headers.update({'User-Agent': useragents.FIREFOX})
        res = self.session.http.get(self.API_URL)
        data = self.session.http.json(res)

        if data['success'] is False:
            raise PluginError(data['reason']['message'])

        try:
            self.title = data['results']['now']['title']
        except KeyError:
            self.title = 'STV'

        return data

    def _get_streams(self):
        hls_url = self._get_api_results()['results']['streamUrl']
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = STV
