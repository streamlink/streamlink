import re
import logging
from uuid import uuid4

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.plugin.api import validate

log = logging.getLogger(__name__)


class Pluto(Plugin):
    url_re_live = re.compile(r'^https?://(?:www\.)?pluto\.tv/live-tv/(?P<slug>[^/]+)$')
    url_re_tv = re.compile(r'^https?://(?:www\.)?pluto\.tv/on-demand/series/(?P<series_slug>[^/]+)/season/\d+/episode/(?P<episode_slug>[^/]+)$')
    url_re_movie = re.compile(r'^https?://(?:www\.)?pluto\.tv/on-demand/movies/(?P<slug>[^/]+)$')

    api_url_live_channels = 'https://api.pluto.tv/v2/channels'
    api_url_tv_series_template = 'http://api.pluto.tv/v3/vod/slugs/%s'
    api_url_movies = 'https://api.pluto.tv/v3/vod/categories?includeItems=true&deviceType=web'

    media_schema = {
        'slug': validate.text,
        validate.optional('stitched'): {
            'urls': [{
                'url': validate.url()
            }]
        }
    }

    live_channels_schema = validate.Schema([
        media_schema
    ])

    tv_schema = validate.Schema({
        'seasons': [{
            'episodes': [
                media_schema
            ]
        }]
    })

    movies_schema = validate.Schema({
        'categories': [{
            'items': [
                media_schema
            ]
        }]
    })

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

            match = next(filter(lambda channel: channel['slug'] == slug, channels_data), None)

        # On-demand TV
        elif self.url_re_tv.match(self.url):
            re_match = self.url_re_tv.match(self.url)
            series_slug = re_match.group('series_slug')
            episode_slug = re_match.group('episode_slug')

            tv_series_res = self.session.http.get(self.api_url_tv_series_template % series_slug)
            tv_series_data = self.session.http.json(tv_series_res, schema=self.tv_schema)

            for season in tv_series_data['seasons']:
                for episode in season['episodes']:
                    if episode['slug'] == episode_slug:
                        match = episode

        # On-demand movie
        elif self.url_re_movie.match(self.url):
            slug = self.url_re_movie.match(self.url).group('slug').lower()

            movies_res = self.session.http.get(self.api_url_movies)
            movies_data = self.session.http.json(movies_res, schema=self.movies_schema)

            for category in movies_data['categories']:
                for movie in category['items']:
                    if movie['slug'] == slug:
                        match = movie

        if not match:
            return

        if 'stitched' not in match:
            log.error('No streams found. This video may use an unsupported format.')
            return

        stream_link_no_sid = match['stitched']['urls'][0]['url']
        sid = str(uuid4())
        stream_link = stream_link_no_sid.replace('&sid=', '&sid=' + sid)

        return HLSStream.parse_variant_playlist(self.session, stream_link)



__plugin__ = Pluto
