import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class StreamMe(Plugin):
    _url_re = re.compile(r'^https?://(?:www\.)?stream\.me/(\w+).*$')

    _streams_schema = validate.Schema(validate.all(
        validate.transform(parse_json),
        validate.any(
            validate.all({
                '_embedded': {
                    'streams': [{
                        'manifest': validate.url(),
                        'active': bool,
                        validate.optional('title'): validate.text,
                        validate.optional('privateLocked'): bool,
                        validate.optional('userSlug'): validate.text,
                    }]
                }},
                validate.get('_embedded'),
                validate.get('streams'),
                validate.get(0),
            ),
            {
                'reasons': [
                    {
                        'message': validate.text,
                        validate.optional('code'): validate.text,
                    }
                ]
            }
        )
    ))
    _formats_schema = validate.Schema(validate.all(
        validate.transform(parse_json),
        {
            'formats': {
                'mp4-hls': {
                    'encodings': [{
                        'videoHeight': int,
                        'location': validate.url()
                    }],
                    validate.optional('origin'): validate.any(None, {
                        validate.optional('location'): validate.url(),
                    })
                }
            }
        },
        validate.get('formats'),
        validate.get('mp4-hls'),
    ))

    API_CHANNEL = 'https://www.stream.me/api-user/v1/{0}/channel'
    STREAM_WEIGHTS = {
        'source': 65535,
    }

    def __init__(self, url):
        super(StreamMe, self).__init__(url)
        self.author = None
        self.title = None
        self.session.http.headers.update({'User-Agent': useragents.FIREFOX})

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        if stream in cls.STREAM_WEIGHTS:
            return cls.STREAM_WEIGHTS[stream], 'streamme'
        return Plugin.stream_weight(stream)

    def get_author(self):
        if self.author is None:
            self._get_channel_data()
        return self.author

    def get_title(self):
        if self.title is None:
            self._get_channel_data()
        return self.title

    def _get_channel_data(self):
        username = self._url_re.match(self.url).group(1)
        data = self.session.http.get(self.API_CHANNEL.format(username),
                                     acceptable_status=(200, 403, 404),
                                     schema=self._streams_schema)
        if data.get('reasons'):
            raise PluginError(data['reasons'][0]['message'])
        self.author = data.get('userSlug')
        self.title = data.get('title')
        return data

    def _get_streams(self):
        data = self._get_channel_data()
        log.trace('{0!r}'.format(data))
        if not data['active']:
            log.error('Stream is not active')
            return

        hls_streams = self.session.http.get(data['manifest'],
                                            schema=self._formats_schema)
        for s in hls_streams['encodings']:
            log.trace('{0!r}'.format(s))
            yield ('{0}p'.format(s['videoHeight']),
                   HLSStream(self.session, s['location']))

        source = hls_streams.get('origin')
        if source:
            log.trace('{0!r}'.format(source))
            yield 'source', HLSStream(self.session, source['location'])


__plugin__ = StreamMe
