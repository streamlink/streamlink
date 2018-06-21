import datetime
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import DASHStream, HLSStream, HTTPStream
from streamlink.utils import parse_json
from streamlink.compat import html_unescape


class RTBF(Plugin):
    GEO_URL = 'https://www.rtbf.be/api/geoloc'
    TOKEN_URL = 'https://token.rtbf.be/'
    RADIO_STREAM_URL = 'http://www.rtbfradioplayer.be/radio/liveradio/rtbf/radios/{}/config.json'

    _url_re = re.compile(r'https?://(?:www\.)?(?:rtbf\.be/auvio/.*\?l?id=(?P<video_id>[0-9]+)#?|rtbfradioplayer\.be/radio/liveradio/.+)')
    _stream_size_re = re.compile(r'https?://.+-(?P<size>\d+p?)\..+?$')

    _video_player_re = re.compile(r'<iframe\s+class="embed-responsive-item\s+js-embed-iframe".*src="(?P<player_url>.+?)".*?</iframe>', re.DOTALL)
    _video_stream_data_re = re.compile(r'<div\s+id="js-embed-player"\s+class="js-embed-player\s+embed-player"\s+data-media="(.+?)"')
    _radio_id_re = re.compile(r'var currentStationKey = "(?P<radio_id>.+?)"')

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
                validate.transform(html_unescape),
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
                    validate.optional('streamUrlDash'): validate.any(None, '', validate.url()),
                    validate.optional('drm'): bool,
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

    def _get_radio_streams(self):
        res = http.get(self.url)
        match = self._radio_id_re.search(res.text)
        if match is None:
            return
        radio_id = match.group('radio_id')
        res = http.get(self.RADIO_STREAM_URL.format(radio_id))
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

        # Check whether streams are DRM-protected
        if stream_data.get('drm', False):
            self.logger.error('Stream is DRM-protected')
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

            dash_url = stream_data.get('urlDash') or stream_data.get('streamUrlDash')
            if dash_url:
                if stream_data.get('isLive', False):
                    # Live streams require a token
                    dash_url = self.tokenize_stream(dash_url)
                for stream in DASHStream.parse_manifest(self.session, dash_url).items():
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
        if match.group('video_id'):
            return self._get_video_streams()
        return self._get_radio_streams()


__plugin__ = RTBF
