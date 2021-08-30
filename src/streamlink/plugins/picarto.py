import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?picarto\.tv/
    (?:(?P<po>streampopout|videopopout)/)?
    (?P<user>[^&?/]+)
    (?:\?tab=videos&id=(?P<vod_id>\d+))?
""", re.VERBOSE))
class Picarto(Plugin):
    channel_schema = validate.Schema({
        'channel': validate.any(None, {
            'stream_name': str,
            'title': str,
            'online': bool,
            'private': bool,
            'categories': [{'label': str}],
        }),
        'getLoadBalancerUrl': {'origin': str},
        'getMultiStreams': validate.any(None, {
            'multistream': bool,
            'streams': [{
                'name': str,
                'online': bool,
            }],
        }),
    })
    vod_schema = validate.Schema({
        'data': {
            'video': validate.any(None, {
                'id': str,
                'title': str,
                'file_name': str,
                'channel': {'name': str},
            }),
        },
    }, validate.get('data'), validate.get('video'))

    HLS_URL = 'https://{origin}.picarto.tv/stream/hls/{file_name}/index.m3u8'

    def get_live(self, username):
        res = self.session.http.get(f'https://ptvintern.picarto.tv/api/channel/detail/{username}')
        channel_data = self.session.http.json(res, schema=self.channel_schema)
        log.trace(f'channel_data={channel_data!r}')

        if not channel_data['channel'] or not channel_data['getMultiStreams']:
            log.debug('Missing channel or streaming data')
            return

        if channel_data['channel']['private']:
            log.info('This is a private stream')
            return

        if channel_data['getMultiStreams']['multistream']:
            msg = 'Found multistream: '
            i = 1
            for user in channel_data['getMultiStreams']['streams']:
                msg += user['name']
                msg += ' (online)' if user['online'] else ' (offline)'
                if i < len(channel_data['getMultiStreams']['streams']):
                    msg += ', '
                i += 1
            log.info(msg)

        if not channel_data['channel']['online']:
            log.error('User is not online')
            return

        self.author = username
        self.category = channel_data['channel']['categories'][0]['label']
        self.title = channel_data['channel']['title']

        return HLSStream.parse_variant_playlist(self.session,
                                                self.HLS_URL.format(file_name=channel_data['channel']['stream_name'],
                                                                    origin=channel_data['getLoadBalancerUrl']['origin']))

    def get_vod(self, vod_id):
        data = {
            'query': (
                'query ($videoId: ID!) {\n'
                '  video(id: $videoId) {\n'
                '    id\n'
                '    title\n'
                '    file_name\n'
                '    channel {\n'
                '      name\n'
                '      }'
                '  }\n'
                '}\n'
            ),
            'variables': {'videoId': vod_id},
        }
        res = self.session.http.post('https://ptvintern.picarto.tv/ptvapi', json=data)
        vod_data = self.session.http.json(res, schema=self.vod_schema)
        log.trace(f'vod_data={vod_data!r}')
        if not vod_data:
            log.debug('Missing video data')
            return

        self.author = vod_data['channel']['name']
        self.category = 'VOD'
        self.title = vod_data['title']
        return HLSStream.parse_variant_playlist(self.session,
                                                self.HLS_URL.format(file_name=vod_data['file_name'],
                                                                    origin='recording-eu-1'))

    def _get_streams(self):
        m = self.match.groupdict()

        if (m['po'] == 'streampopout' or not m['po']) and m['user'] and not m['vod_id']:
            log.debug('Type=Live')
            return self.get_live(m['user'])
        elif m['po'] == 'videopopout' or (m['user'] and m['vod_id']):
            log.debug('Type=VOD')
            vod_id = m['vod_id'] if m['vod_id'] else m['user']
            return self.get_vod(vod_id)


__plugin__ = Picarto
