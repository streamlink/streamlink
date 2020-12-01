import logging
import re
from uuid import uuid4

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


class Pluto(Plugin):
    _re_url = re.compile(r'''^https?://(?:www\.)?pluto\.tv/(?:
        live-tv/(?P<slug_live>[^/?]+)/?$
        |
        on-demand/series/(?P<slug_series>[^/]+)/season/\d+/episode/(?P<slug_episode>[^/]+)$
        |
        on-demand/movies/(?P<slug_movies>[^/]+)$
    )''', re.VERBOSE)

    title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

    def get_title(self):
        return self.title

    def _schema_media(self, slug):
        return validate.Schema(
            [{
                'name': str,
                'slug': str,
                validate.optional('stitched'): {
                    'urls': [
                        {
                            'type': str,
                            'url': validate.url(),
                        }
                    ]
                }
            }],
            validate.filter(lambda k: k['slug'].lower() == slug.lower()),
            validate.get(0),
        )

    def _get_streams(self):
        data = None

        m = self._re_url.match(self.url).groupdict()
        if m['slug_live']:
            res = self.session.http.get('https://api.pluto.tv/v2/channels')
            data = self.session.http.json(res,
                                          schema=self._schema_media(m['slug_live']))
        elif m['slug_series'] and m['slug_episode']:
            res = self.session.http.get(f'http://api.pluto.tv/v3/vod/slugs/{m["slug_series"]}')
            data = self.session.http.json(
                res,
                schema=validate.Schema(
                    {'seasons': validate.all(
                        [{'episodes': self._schema_media(m['slug_episode'])}],
                        validate.filter(lambda k: k['episodes'] is not None))},
                    validate.get('seasons'),
                    validate.get(0),
                    validate.any(None, validate.get('episodes'))
                ),
            )
        elif m['slug_movies']:
            res = self.session.http.get('https://api.pluto.tv/v3/vod/categories',
                                        params={'includeItems': 'true', 'deviceType': 'web'})
            data = self.session.http.json(
                res,
                schema=validate.Schema(
                    {'categories': validate.all(
                        [{'items': self._schema_media(m['slug_movies'])}],
                        validate.filter(lambda k: k['items'] is not None))},
                    validate.get('categories'),
                    validate.get(0),
                    validate.any(None, validate.get('items')),
                ),
            )

        log.trace(f'{data!r}')
        if data is None or not data.get('stitched'):
            return

        self.title = data['name']
        stream_url_no_sid = data['stitched']['urls'][0]['url']
        device_id = str(uuid4())
        stream_url = update_qsd(stream_url_no_sid, {
            'deviceId': device_id,
            'sid': device_id,
            'deviceType': 'web',
            'deviceMake': 'Firefox',
            'deviceModel': 'Firefox',
            'appName': 'web',
        })

        self.session.set_option('ffmpeg-fout', 'mpegts')
        for q, s in HLSStream.parse_variant_playlist(self.session, stream_url).items():
            yield q, MuxedStream(self.session, s)


__plugin__ = Pluto
