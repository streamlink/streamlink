import logging
import re

from uuid import uuid4

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


class Pluto(Plugin):
    url_re_live = re.compile(r'https?://(?:www\.)?pluto\.tv/live-tv/(?P<slug>[^/?]+)/?$')
    url_re_tv = re.compile(r'^https?://(?:www\.)?pluto\.tv/on-demand/series/(?P<series_slug>[^/]+)/season/\d+/episode/(?P<episode_slug>[^/]+)$')
    url_re_movie = re.compile(r'^https?://(?:www\.)?pluto\.tv/on-demand/movies/(?P<slug>[^/]+)$')

    api_url_live_channels = 'https://api.pluto.tv/v2/channels'
    api_url_tv_series_template = 'http://api.pluto.tv/v3/vod/slugs/{0}'
    api_url_movies = 'https://api.pluto.tv/v3/vod/categories?includeItems=true&deviceType=web'

    media_schema = {
        'slug': validate.text,
        validate.optional('stitched'): {
            'urls': [{
                'url': validate.url()
            }]
        }
    }
    live_channels_schema = validate.Schema([media_schema])
    tv_schema = validate.Schema({'seasons': [{'episodes': [media_schema]}]})
    movies_schema = validate.Schema({'categories': [{'items': [media_schema]}]})

    @classmethod
    def can_handle_url(cls, url):
        return (
            cls.url_re_live.match(url)
            or cls.url_re_tv.match(url)
            or cls.url_re_movie.match(url)
        )

    def _get_streams(self):
        match = None

        # live TV
        if self.url_re_live.match(self.url):
            slug = self.url_re_live.match(self.url).group('slug').lower()

            channels_res = self.session.http.get(self.api_url_live_channels)
            channels_data = self.session.http.json(channels_res, schema=self.live_channels_schema)

            c_list = set()
            for _d in channels_data:
                c_list.add(_d['slug'])
            log.trace('Available channels: {0}'.format(', '.join(sorted(c_list))))

            for channel in channels_data:
                if channel['slug'] == slug:
                    match = channel
                    break

        # On-demand TV
        elif self.url_re_tv.match(self.url):
            re_match = self.url_re_tv.match(self.url)
            series_slug = re_match.group('series_slug')
            episode_slug = re_match.group('episode_slug')

            tv_series_res = self.session.http.get(self.api_url_tv_series_template.format(series_slug))
            tv_series_data = self.session.http.json(tv_series_res, schema=self.tv_schema)

            for season in tv_series_data['seasons']:
                for episode in season['episodes']:
                    if episode['slug'] == episode_slug:
                        match = episode
                        break

        # On-demand movie
        elif self.url_re_movie.match(self.url):
            slug = self.url_re_movie.match(self.url).group('slug').lower()

            movies_res = self.session.http.get(self.api_url_movies)
            movies_data = self.session.http.json(movies_res, schema=self.movies_schema)

            for category in movies_data['categories']:
                for movie in category['items']:
                    if movie['slug'] == slug:
                        match = movie
                        break

        if not match:
            return

        if 'stitched' not in match:
            log.error('No streams found. This video may use an unsupported format.')
            return

        stream_link_no_sid = match['stitched']['urls'][0]['url']

        device_id = str(uuid4())
        stream_url = update_qsd(stream_link_no_sid, {
            'deviceId': device_id,
            'sid': device_id,
            'deviceType': 'web',
            'deviceMake': 'Firefox',
            'deviceModel': 'Firefox',
            'appName': 'web',
        })
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = Pluto
