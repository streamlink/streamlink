"""
$description Indian Hindi-language news channel covering world & Indian news, business, entertainment and sport.
$url zeenews.india.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://zeenews\.india\.com/live-tv'
))
class ZeeNews(Plugin):
    HLS_URL = 'https://z5ams.akamaized.net/zeenews/index.m3u8{0}'
    TOKEN_URL = 'https://useraction.zee5.com/token/live.php'

    title = 'Zee News'

    def _get_streams(self):
        res = self.session.http.get(self.TOKEN_URL)
        token = self.session.http.json(res)['video_token']
        log.debug('video_token: {0}'.format(token))
        yield from HLSStream.parse_variant_playlist(self.session, self.HLS_URL.format(token)).items()


__plugin__ = ZeeNews
