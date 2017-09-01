from functools import partial
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream
from streamlink.utils import parse_json, update_scheme


class Bloomberg(Plugin):
    VOD_API_URL = 'https://www.bloomberg.com/api/embed?id={0}'
    PLAYER_URL = 'https://cdn.gotraffic.net/projector/latest/bplayer.js'
    CHANNEL_MAP = {
        'audio': 'BBG_RADIO',
        'live/europe': 'EU',
        'live/us': 'US',
        'live/asia': 'ASIA',
        'live/stream': 'EVENT',
        'live/emea': 'EMEA_EVENT',
        'live/asia_stream': 'ASIA_EVENT'
    }

    _url_re = re.compile(r'''
        https?://www\.bloomberg\.com/(
            news/videos/[^/]+/[^/]+ |
            (?P<channel>live/(?:stream|emea|asia_stream|europe|us|asia)|audio)/?
        )
''', re.VERBOSE)
    _live_player_re = re.compile(r'{APP_BUNDLE:"(?P<live_player_url>.+?/app.js)"')
    _js_to_json_re = partial(re.compile(r'(\w+):(["\']|\d?\.?\d+,|true|false|\[|{)').sub, r'"\1":\2')
    _video_id_re = re.compile(r'data-bmmr-id=\\"(?P<video_id>.+?)\\"')
    _mp4_bitrate_re = re.compile(r'.*_(?P<bitrate>[0-9]+)\.mp4')

    _live_streams_schema = validate.Schema(
        validate.transform(_js_to_json_re),
        validate.transform(lambda x: x.replace(':.', ':0.')),
        validate.transform(parse_json),
        validate.Schema(
            {
                'cdns': validate.all(
                    [
                        validate.Schema(
                            {
                                'streams': validate.all([
                                    validate.Schema(
                                        {'url': validate.transform(lambda x: re.sub(r'(https?:/)([^/])', r'\1/\2', x))},
                                        validate.get('url'),
                                        validate.url()
                                    )
                                ]),
                            },
                            validate.get('streams')
                        )
                    ],
                    validate.transform(lambda x: [i for y in x for i in y])
                )
            },
            validate.get('cdns')
        )
    )

    _vod_api_schema = validate.Schema(
        {
            'secureStreams': validate.all([
                validate.Schema(
                    {'url': validate.url()},
                    validate.get('url')
                )
            ]),
            'streams': validate.all([
                validate.Schema(
                    {'url': validate.url()},
                    validate.get('url')
                )
            ]),
            'contentLoc': validate.url(),
        },
        validate.transform(lambda x: list(set(x['secureStreams'] + x['streams'] + [x['contentLoc']])))
    )

    @classmethod
    def can_handle_url(cls, url):
        return Bloomberg._url_re.match(url)

    def _get_live_streams(self):
        # Get channel id
        match = self._url_re.match(self.url)
        channel = match.group('channel')

        # Retrieve live player URL
        res = http.get(self.PLAYER_URL)
        match = self._live_player_re.search(res.text)
        if match is None:
            return []
        live_player_url = update_scheme(self.url, match.group('live_player_url'))

        # Extract streams from the live player page
        res = http.get(live_player_url)
        stream_datas = re.findall(r'{0}(?:_MINI)?:({{.+?}}]}}]}})'.format(self.CHANNEL_MAP[channel]), res.text)
        streams = []
        for s in stream_datas:
            for u in self._live_streams_schema.validate(s):
                if u not in streams:
                    streams.append(u)

        return streams

    def _get_vod_streams(self):
        # Retrieve URL page and search for video ID
        res = http.get(self.url)
        match = self._video_id_re.search(res.text)
        if match is None:
            return []
        video_id = match.group('video_id')

        res = http.get(self.VOD_API_URL.format(video_id))
        streams = http.json(res, schema=self._vod_api_schema)
        return streams

    def _get_streams(self):
        if '/news/videos/' in self.url:
            # VOD
            streams = self._get_vod_streams()
        else:
            # Live
            streams = self._get_live_streams()

        for video_url in streams:
            if '.f4m' in video_url:
                for stream in HDSStream.parse_manifest(self.session, video_url).items():
                    yield stream
            elif '.m3u8' in video_url:
                for stream in HLSStream.parse_variant_playlist(self.session, video_url).items():
                    yield stream
            if '.mp4' in video_url:
                match = self._mp4_bitrate_re.match(video_url)
                if match is not None:
                    bitrate = match.group('bitrate') + 'k'
                else:
                    bitrate = 'vod'
                yield bitrate, HTTPStream(self.session, video_url)


__plugin__ = Bloomberg
