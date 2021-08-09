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
    url_re = re.compile(r'https?://(?:www\.)?nbcnews\.com/now')
    json_data_re = re.compile(
        r'<script type="application/ld+json">({.*?})</script>'
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

    def _get_video_id(self, site_url):
        maininfo_res = self.session.http.get(site_url)
        video_info_json = re.findall(r'<script type="application/ld\+json">(.*?)</script>', maininfo_res.text)[0]
        video_info_json = parse_json(video_info_json)
        embedUrl = video_info_json["embedUrl"]
        video_id = embedUrl.split("/")[-1]
        return video_id

    def _get_streams(self):
        video_id = self._get_video_id(self.url)
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
