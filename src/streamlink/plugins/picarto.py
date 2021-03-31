import logging
import re
import time
from urllib.parse import unquote_plus, urlparse

import websocket

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Picarto(Plugin):
    url_re = re.compile(r'''
        https?://(?:www\.)?picarto\.tv/
            (?:(?P<po>streampopout|videopopout)/)?
            (?P<user>[^&?/]+)
            (?:\?tab=videos&id=(?P<vod_id>\d+))?
    ''', re.VERBOSE)

    channel_api_url = 'https://ptvintern.picarto.tv/api/channel/detail/{0}'
    vod_api_url = 'https://ptvintern.picarto.tv/ptvapi'
    live_wss_url = 'wss://{server}/stream/json_golive%2B{data}.js'
    vod_wss_server = 'recording-eu-1.picarto.tv'
    vod_wss_url = 'wss://{server}/stream/json_{data}.js'

    channel_schema = validate.Schema({
        'channel': validate.any(None, {
            'title': str,
            'online': bool,
            'private': bool,
            'categories': [{
                'label': str,
            }],
        }),
        'getLoadBalancerUrl': {
            'url': validate.url(),
        },
        'getMultiStreams': validate.any(None, {
            'multistream': bool,
            'streams': [{
                'name': str,
                'online': bool,
            }],
        }),
    })
    stream_schema = validate.Schema(validate.any({'error': str}, {
        'source': [{
            'type': str,
            'url': validate.url(),
        }],
    }), validate.get('source'))
    vod_schema = validate.Schema({
        'data': {
            'video': validate.any(None, {
                'id': str,
                'title': str,
                'file_name': str,
                'channel': {
                    'name': str,
                },
            }),
        },
    }, validate.get('data'), validate.get('video'))

    author = None
    category = None
    title = None

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_author(self):
        return self.author

    def get_category(self):
        return self.category

    def get_title(self):
        return self.title

    def parse_proxy_url(self, purl):
        '''Adapted from UStreamTV plugin (ustreamtv.py)'''

        proxy_options = {}
        if purl:
            p = urlparse(purl)
            proxy_options['proxy_type'] = p.scheme
            proxy_options['http_proxy_host'] = p.hostname
            if p.port:
                proxy_options['http_proxy_port'] = p.port
            if p.username:
                proxy_options['http_proxy_auth'] = \
                    (unquote_plus(p.username), unquote_plus(p.password or ''))
        return proxy_options

    def get_stream(self, data, live=True, server=None):
        # Proxy support adapted from the UStreamTV plugin (ustreamtv.py)
        proxy_url = self.session.get_option('https-proxy')
        if proxy_url is None:
            proxy_url = self.session.get_option('http-proxy')
        proxy_options = self.parse_proxy_url(proxy_url)
        if proxy_options.get('http_proxy_host'):
            log.debug('Using proxy ({0}://{1}:{2})'.format(
                proxy_options.get('proxy_type') or 'http',
                proxy_options.get('http_proxy_host'),
                proxy_options.get('http_proxy_port') or 80))

        if live and server:
            wss_url = self.live_wss_url.format(server=server, data=data)
        else:
            wss_url = self.vod_wss_url.format(server=self.vod_wss_server, data=data)

        ws = websocket.create_connection(
            wss_url,
            header={'User-Agent': useragents.FIREFOX},
            **proxy_options,
        )
        for i in range(50):
            res = ws.recv()
            if 'error' in res:
                time.sleep(0.1)
            else:
                log.debug(f'Got WS reply with {i * 100}ms delay')
                break

        if 'error' in res:
            log.error('Failed to get WS reply')
            return

        ws.close()
        stream_data = parse_json(res, schema=self.stream_schema)

        for s in stream_data:
            if s['type'] == 'html5/application/vnd.apple.mpegurl':
                yield from HLSStream.parse_variant_playlist(self.session, s['url']).items()

    def get_live(self, username):
        res = self.session.http.get(self.channel_api_url.format(username))
        channel_data = self.session.http.json(res, schema=self.channel_schema)

        if not channel_data['channel'] or not channel_data['getMultiStreams']:
            log.debug('Missing channel or streaming data')
            return

        if channel_data['channel']['private']:
            log.error('This is a private stream')
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

        p = urlparse(channel_data['getLoadBalancerUrl']['url'])
        return self.get_stream(username, live=True, server=p.netloc)

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
        res = self.session.http.post(self.vod_api_url, json=data)
        vod_data = self.session.http.json(res, schema=self.vod_schema)
        if not vod_data:
            log.debug('Missing video data')
            return

        self.author = vod_data['channel']['name']
        self.category = 'VOD'
        self.title = vod_data['title']

        return self.get_stream(vod_data['file_name'], live=False)

    def _get_streams(self):
        m = self.url_re.match(self.url).groupdict()

        if (m['po'] == 'streampopout' or not m['po']) and m['user'] and not m['vod_id']:
            log.debug('Type=Live')
            return self.get_live(m['user'])
        elif m['po'] == 'videopopout' or (m['user'] and m['vod_id']):
            log.debug('Type=VOD')
            vod_id = m['vod_id'] if m['vod_id'] else m['user']
            return self.get_vod(vod_id)


__plugin__ = Picarto
