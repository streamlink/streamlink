import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.plugin.api import validate

log = logging.getLogger(__name__)


class WASD(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?wasd\.tv/channel/(?P<channel_id>\d+)(?:/videos/(?P<video_id>\d+))?')
    _media_schema = validate.Schema({
        'user_id': int,
        'media_container_streams': [{
            'stream_status': validate.text,
            'stream_online_status': validate.text,
            'user_id': int,
            'stream_media': [{
                'media_id': int,
                'media_meta': {
                    'media_url': validate.any(validate.text, None),
                    'media_archive_url': validate.any(validate.text, None),
                },
                'media_status': validate.any('STOPPED', 'RUNNING'),
                'media_type': 'HLS',
                'user_id': int,
            }]
        }],
    })
    _api_schema = validate.Schema({
        'result':
            validate.any(
                _media_schema,
                validate.all(list,
                             validate.get(0),
                             _media_schema),
                [],
            ),
    }, validate.get('result'))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        m = self._url_re.match(self.url)
        video_id = m.group('video_id')
        channel_id = m.group('channel_id')

        self.session.http.post('https://wasd.tv/api/auth/anon-token')

        if video_id:
            res = self.session.http.get('https://wasd.tv/api/media-containers/{0}'.format(video_id))
        else:
            res = self.session.http.get(
                'https://wasd.tv/api/media-containers',
                params={
                    'media_container_status': 'RUNNING',
                    'limit': '1',
                    'offset': '0',
                    'channel_id': channel_id,
                    'media_container_type': 'SINGLE,COOP',
                }
            )

        json_res = self.session.http.json(res, schema=self._api_schema)
        log.trace('{0!r}'.format(json_res))
        if not json_res:
            raise PluginError('No data returned from URL={0}'.format(res.url))

        for stream in json_res['media_container_streams']:
            if stream['user_id'] == json_res['user_id']:
                log.debug('stream_status: {0}, stream_online_status: {1}'.format(
                    stream['stream_status'], stream['stream_online_status']))
                for stream in stream['stream_media']:
                    if stream['media_status'] == 'STOPPED':
                        hls_url = stream['media_meta']['media_archive_url']
                    elif stream['media_status'] == 'RUNNING':
                        hls_url = stream['media_meta']['media_url']

                    for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                        yield s


__plugin__ = WASD
