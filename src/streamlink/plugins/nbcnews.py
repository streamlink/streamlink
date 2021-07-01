import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?nbcnews\.com/now'
))
class NBCNews(Plugin):
    json_data_re = re.compile(
        r'<script id="__NEXT_DATA__" type="application/json">({.*})</script>'
    )
    api_url = 'https://stream.nbcnews.com/data/live_sources_{}.json'
    token_url = 'https://tokens.playmakerservices.com/'

    api_schema = validate.Schema(
        validate.transform(parse_json), {
            'videoSources': [{
                'sourceUrl': validate.url(),
                'type': validate.text,
            }],
        },
        validate.get('videoSources'),
        validate.get(0),
    )

    json_data_schema = validate.Schema(
        validate.transform(json_data_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json), {
                'props': {'initialState': {'front': {'curation': {
                    'layouts': [{'packages': [{'metadata': {
                        validate.optional('playmakerIdOverride'): str,
                    }}]}],
                }}}},
            },
            validate.get('props'),
            validate.get('initialState'),
            validate.get('front'),
            validate.get('curation'),
            validate.get('layouts'),
            validate.get(0),
            validate.get('packages'),
            validate.get(1),
            validate.get('metadata'),
            validate.get('playmakerIdOverride'),
        )),
    )

    token_schema = validate.Schema(
        validate.transform(parse_json),
        {'akamai': [{
            'tokenizedUrl': validate.url(),
        }]},
        validate.get('akamai'),
        validate.get(0),
        validate.get('tokenizedUrl'),
    )

    def get_title(self):
        return 'NBC News Now'

    @Plugin.broken(3123)
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
