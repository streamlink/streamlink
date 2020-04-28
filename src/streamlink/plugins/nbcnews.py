import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class NBCNews(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?nbcnews\.com/now')
    js_re = re.compile(r'https://ndassets\.s-nbcnews\.com/main-[0-9a-f]{20}\.js')
    api_re = re.compile(r'NEWS_NOW_PID="([0-9]+)"')
    api_url = 'https://stream.nbcnews.com/data/live_sources_{0}.json'
    api_schema = validate.Schema(validate.transform(parse_json), {
        'videoSources': [{
            'sourceUrl': validate.url(),
            'type': validate.text
        }]
    }, validate.get('videoSources'), validate.get(0))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_title(self):
        return 'NBC News Now'

    def _get_streams(self):
        html = self.session.http.get(self.url).text
        match = self.js_re.search(html)
        js = self.session.http.get(match.group(0)).text
        match = self.api_re.search(js)
        log.debug('API ID: {0}'.format(match.group(1)))
        api_url = self.api_url.format(match.group(1))
        stream = self.session.http.get(api_url, schema=self.api_schema)
        log.trace('{0!r}'.format(stream))
        if stream['type'].lower() != 'live':
            log.error('invalid stream type "{0}"'.format(stream['type']))
            return
        return HLSStream.parse_variant_playlist(self.session, stream['sourceUrl'])


__plugin__ = NBCNews
