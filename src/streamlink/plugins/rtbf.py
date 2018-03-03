import datetime
try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json


class RTBF(Plugin):
    GEO_URL = 'https://www.rtbf.be/api/geoloc'
    TOKEN_URL = 'https://token.rtbf.be/'
    RADIO_STREAM_URL = 'http://www.rtbfradioplayer.be/radio/liveradio/rtbf/radios/{}/config.json'

    _url_re = re.compile(r'https?://(?:www\.)?(?:rtbf\.be/auvio/.*\?l?id=(?P<video_id>[0-9]+)#?|rtbfradioplayer\.be/radio/liveradio/(?:webradio-)?(?P<radio>.+))')
    _stream_size_re = re.compile(r'https?://.+-(?P<size>\d+p?)\..+?$')

    _video_player_re = re.compile(r'<iframe\s+class="embed-responsive-item\s+js-embed-iframe".*src="(?P<player_url>.+?)".*?</iframe>', re.DOTALL)
    _video_stream_data_re = re.compile(r'<div\s+id="js-embed-player"\s+class="js-embed-player\s+embed-player"\s+data-media="(.+?)"')

    _geo_schema = validate.Schema(
        {
            'country': validate.text,
            'zone': validate.text
        }
    )

    _video_stream_schema = validate.Schema(
        validate.transform(_video_stream_data_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(HTMLParser().unescape),
                validate.transform(parse_json),
                {
                    'geoLocRestriction': validate.text,
                    validate.optional('isLive'): bool,
                    validate.optional('startDate'): validate.text,
                    validate.optional('endDate'): validate.text,
                    'sources': validate.any(
                        [],
                        validate.Schema({
                            validate.text: validate.any(None, '', validate.url())
                        })
                    ),
                    validate.optional('urlHls'): validate.any(None, '', validate.url()),
                    validate.optional('urlDash'): validate.any(None, '', validate.url()),
                    validate.optional('streamUrlHls'): validate.any(None, '', validate.url()),
                    validate.optional('streamUrlDash'): validate.any(None, '', validate.url())
                }
            )
        )
    )

    _radio_stream_schema = validate.Schema(
        {
            'audioUrls': validate.all(
                [{
                    'url': validate.url(),
                    'mimeType': validate.text
                }]
            )
        }
    )

    @classmethod
    def check_geolocation(cls, geoloc_flag):
        if geoloc_flag == 'open':
            return True

        res = http.get(cls.GEO_URL)
        data = http.json(res, schema=cls._geo_schema)
        return data['country'] == geoloc_flag or data['zone'] == geoloc_flag

    @classmethod
    def tokenize_stream(cls, url):
        res = http.post(cls.TOKEN_URL, data={'streams[url]': url})
        data = http.json(res)
        return data['streams']['url']

    @staticmethod
    def iso8601_to_epoch(date):
        # Convert an ISO 8601-formatted string date to datetime
        return datetime.datetime.strptime(date[:-6], '%Y-%m-%dT%H:%M:%S') + \
            datetime.timedelta(hours=int(date[-6:-3]), minutes=int(date[-2:]))

    @classmethod
    def can_handle_url(cls, url):
        return RTBF._url_re.match(url)

    def _get_radio_streams(self, radio):
        res = http.get(self.RADIO_STREAM_URL.format(radio.replace('-', '_')))
        streams = http.json(res, schema=self._radio_stream_schema)

        for stream in streams['audioUrls']:
            match = self._stream_size_re.match(stream['url'])
            if match is not None:
                quality = '{}k'.format(match.group('size'))
            else:
                quality = stream['mimetype']
            yield quality, HTTPStream(self.session, stream['url'])

    def _get_video_streams(self):
        res = http.get(self.url)
        match = self._video_player_re.search(res.text)
        if match is None:
            return
        player_url = match.group('player_url')
        stream_data = http.get(player_url, schema=self._video_stream_schema)
        if stream_data is None:
            return

        # Check geolocation to prevent further errors when stream is parsed
        if not self.check_geolocation(stream_data['geoLocRestriction']):
            self.logger.error('Stream is geo-restricted')
            return

        now = datetime.datetime.now()
        try:
            if isinstance(stream_data['sources'], dict):
                urls = []
                for profile, url in stream_data['sources'].items():
                    if not url or url in urls:
                        continue
                    match = self._stream_size_re.match(url)
                    if match is not None:
                        quality = match.group('size')
                    else:
                        quality = profile
                    yield quality, HTTPStream(self.session, url)
                    urls.append(url)

            hls_url = stream_data.get('urlHls') or stream_data.get('streamUrlHls')
            if hls_url:
                if stream_data.get('isLive', False):
                    # Live streams require a token
                    hls_url = self.tokenize_stream(hls_url)
                for stream in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                    yield stream

        except IOError as err:
            if '403 Client Error' in str(err):
                # Check whether video is expired
                if 'startDate' in stream_data:
                    if now < self.iso8601_to_epoch(stream_data['startDate']):
                        self.logger.error('Stream is not yet available')
                elif 'endDate' in stream_data:
                    if now > self.iso8601_to_epoch(stream_data['endDate']):
                        self.logger.error('Stream has expired')

    def _get_streams(self):
        match = self.can_handle_url(self.url)
        if match.group('radio'):
            return self._get_radio_streams(match.group('radio'))
        return self._get_video_streams()


__plugin__ = RTBF
