import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class ZeeNews(Plugin):
    _url_re = re.compile(r'https?://zeenews\.india\.com/live-tv')

    HLS_URL = 'https://z5ams.akamaized.net/zeenews/index.m3u8{0}'
    TOKEN_URL = 'https://useraction.zee5.com/token/live.php'

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def get_title(self):
        return 'Zee News'

    def _get_streams(self):
        res = self.session.http.get(self.TOKEN_URL)
        token = self.session.http.json(res)['video_token']
        log.debug('video_token: {0}'.format(token))
        yield from HLSStream.parse_variant_playlist(self.session, self.HLS_URL.format(token)).items()


__plugin__ = ZeeNews
