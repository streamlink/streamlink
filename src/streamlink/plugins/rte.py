from datetime import datetime
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream


class RTE(Plugin):
    VOD_API_URL = 'http://www.rte.ie/rteavgen/getplaylist/?type=web&format=json&id={0}'
    LIVE_API_URL = 'http://feeds.rasset.ie/livelistings/playlist'

    _url_re = re.compile(r'https?://www\.rte\.ie/player/[a-z0-9]+/(?:show/[a-z-]+-[0-9]+/(?P<video_id>[0-9]+)|live/(?P<channel_id>[0-9]+))')
    _vod_api_schema = validate.Schema({
        'current_date': validate.text,
        'shows': validate.Schema(
            list,
            validate.length(1),
            validate.get(0),
            validate.Schema({
                'valid_start': validate.text,
                'valid_end': validate.text,
                'media:group': validate.Schema(
                    list,
                    validate.length(1),
                    validate.get(0),
                    validate.Schema(
                        {
                            'hls_server': validate.url(),
                            'hls_url': validate.text,
                            'hds_server': validate.url(),
                            'hds_url': validate.text,
                            # API returns RTMP streams that don't seem to work, ignore them
                            # 'url': validate.any(
                            #     validate.url(scheme="rtmp"),
                            #     validate.url(scheme="rtmpe")
                            # )
                        },
                        validate.transform(lambda x: [x['hls_server'] + x['hls_url'], x['hds_server'] + x['hds_url']])
                    ),
                ),
            }),
        )
    })

    _live_api_schema = validate.Schema(
        validate.xml_findall('.//{http://search.yahoo.com/mrss/}content'),
        [
            validate.all(
                validate.xml_element(attrib={'url': validate.url()}),
                validate.get('url')
            )
        ]
    )
    _live_api_iphone_schema = validate.Schema(
        list,
        validate.length(1),
        validate.get(0),
        validate.Schema(
            {'fullUrl': validate.any(validate.url(), 'none')},
            validate.get('fullUrl')
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return RTE._url_re.match(url)

    def _get_streams(self):
        match = self._url_re.match(self.url)
        video_id = match.group('video_id')

        if video_id is not None:
            # VOD
            res = http.get(self.VOD_API_URL.format(video_id))
            stream_data = http.json(res, schema=self._vod_api_schema)

            # Check whether video format is expired
            current_date = datetime.strptime(stream_data['current_date'], '%Y-%m-%dT%H:%M:%S.%f')
            valid_start = datetime.strptime(stream_data['shows']['valid_start'], '%Y-%m-%dT%H:%M:%S')
            valid_end = datetime.strptime(stream_data['shows']['valid_end'], '%Y-%m-%dT%H:%M:%S')
            if current_date < valid_start or current_date > valid_end:
                self.logger.error('Failed to access stream, may be due to expired content')
                return

            streams = stream_data['shows']['media:group']
        else:
            # Live
            channel_id = match.group('channel_id')
            # Get live streams for desktop
            res = http.get(self.LIVE_API_URL, params={'channelid': channel_id})
            streams = http.xml(res, schema=self._live_api_schema)

            # Get HLS streams for Iphone
            res = http.get(self.LIVE_API_URL, params={'channelid': channel_id, 'platform': 'iphone'})
            stream = http.json(res, schema=self._live_api_iphone_schema)
            if stream != 'none':
                streams.append(stream)

        for stream in streams:
            if '.f4m' in stream:
                for s in HDSStream.parse_manifest(self.session, stream).items():
                    yield s
            if '.m3u8' in stream:
                for s in HLSStream.parse_variant_playlist(self.session, stream).items():
                    yield s


__plugin__ = RTE
