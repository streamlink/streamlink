import logging
import re
from functools import partial

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate, useragents
from streamlink.stream import HDSStream, HLSStream, HTTPStream
from streamlink.utils import parse_json, update_scheme

log = logging.getLogger(__name__)


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
        https?://(?:www\.)?bloomberg\.com/
        (?:
            news/videos/[^/]+/[^/]+|
            live/(?P<channel>.+)/?
        )
''', re.VERBOSE)
    _live_player_re = re.compile(r'{APP_BUNDLE:"(?P<live_player_url>.+?/app.js)"')
    _js_to_json_re = partial(re.compile(r'(\w+):(["\']|\d?\.?\d+,|true|false|\[|{)').sub, r'"\1":\2')
    _video_id_re = re.compile(r'data-bmmr-id=\\"(?P<video_id>.+?)\\"')
    _mp4_bitrate_re = re.compile(r'.*_(?P<bitrate>[0-9]+)\.mp4')
    _preload_state_re = re.compile(r'window.__PRELOADED_STATE__\s*=\s*({.*});', re.DOTALL)
    _live_stream_info_re = re.compile(r'12:.*t.exports=({.*})},{}],13:', re.DOTALL)

    _live_streams_schema = validate.Schema(
        validate.transform(_js_to_json_re),
        validate.transform(lambda x: x.replace(':.', ':0.')),
        validate.transform(parse_json),
        validate.Schema({
            validate.text: {
                validate.optional('cdns'): validate.all(
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
            }
        },
        )
    )

    _channel_list_schema = validate.Schema(
        validate.transform(parse_json),
        {"live": {"channels": {"byChannelId": {
            validate.text: validate.all({"liveId": validate.text}, validate.get("liveId"))
        }}}},
        validate.get("live"),
        validate.get("channels"),
        validate.get("byChannelId"),
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

        res = self.session.http.get(self.url, headers={
            "authority": "www.bloomberg.com",
            "upgrade-insecure-requests": "1",
            "dnt": "1",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3"
        })
        if "Are you a robot?" in res.text:
            log.error("Are you a robot?")
        match = self._preload_state_re.search(res.text)
        if match:
            live_ids = self._channel_list_schema.validate(match.group(1))
            live_id = live_ids.get(channel)
            if live_id:
                log.debug("Found liveId = {0}".format(live_id))
                # Retrieve live player URL
                res = self.session.http.get(self.PLAYER_URL)
                match = self._live_player_re.search(res.text)
                if match is None:
                    return []
                live_player_url = update_scheme(self.url, match.group('live_player_url'))

                # Extract streams from the live player page
                log.debug("Player URL: {0}".format(live_player_url))
                res = self.session.http.get(live_player_url)
                match = self._live_stream_info_re.search(res.text)
                if match:
                    stream_info = self._live_streams_schema.validate(match.group(1))
                    data = stream_info.get(live_id, {})
                    return data.get('cdns', [])
            else:
                log.error("Could not find liveId for channel '{0}'".format(channel))

        return []

    def _get_vod_streams(self):
        # Retrieve URL page and search for video ID
        res = self.session.http.get(self.url)
        match = self._video_id_re.search(res.text)
        if match is None:
            return []
        video_id = match.group('video_id')

        res = self.session.http.get(self.VOD_API_URL.format(video_id))
        streams = self.session.http.json(res, schema=self._vod_api_schema)
        return streams

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        if '/news/videos/' in self.url:
            # VOD
            streams = self._get_vod_streams()
        else:
            # Live
            streams = self._get_live_streams()

        for video_url in streams:
            log.debug("Found stream: {0}".format(video_url))
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
