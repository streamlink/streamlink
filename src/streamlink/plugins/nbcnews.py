import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class NBCNews(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?nbcnews\.com/now')
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

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_title(self):
        return 'NBC News Now'

    def _get_streams(self):
        video_id = self.session.http.get(self.url, schema=self.json_data_schema)
        log.debug('API ID: {0}'.format(video_id))

        api_url = self.api_url.format(video_id)
        stream = self.session.http.get(api_url, schema=self.api_schema)
        log.trace('{0!r}'.format(stream))
        if stream['type'].lower() != 'live':
            log.error('Invalid stream type "{0}"'.format(stream['type']))
            return

        json_post_data = {
            'requestorId': 'nbcnews',
            'pid': video_id,
            'application': 'NBCSports',
            'version': 'v1',
            'platform': 'desktop',
            'token': '',
            'resourceId': '',
            'inPath': 'false',
            'authenticationType': 'unauth',
            'cdn': 'akamai',
            'url': stream['sourceUrl'],
        }
        url = self.session.http.post(
            self.token_url,
            json=json_post_data,
            schema=self.token_schema,
        )
        return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = NBCNews
