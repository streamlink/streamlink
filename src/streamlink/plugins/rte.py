from datetime import datetime
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream


class RTE(Plugin):
    VOD_API_URL = 'http://feeds.rasset.ie/rteavgen/player/playlist/?type=iptv&format=json&showId={0}'
    LIVE_API_URL = 'http://feeds.rasset.ie/livelistings/playlist/?channelid={0}'

    _url_re = re.compile(r'http://www\.rte\.ie/player/[a-z0-9]+/(?:show/[a-z-]+-[0-9]+/(?P<video_id>[0-9]+)|live/(?P<channel_id>[0-9]+))')

    _vod_api_schema = validate.Schema({
        'current_date': validate.text,
        'shows': validate.all(
            [{
                'valid_start': validate.text,
                'valid_end': validate.text,
                'media:group': validate.all(
                    [
                        validate.Schema(
                            {
                                'rte:server': validate.url(),
                                'url': validate.text,
                            },
                            validate.transform(lambda x: x['rte:server'] + x['url'])
                        )
                    ]
                )
            }]
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

    @classmethod
    def can_handle_url(cls, url):
        return RTE._url_re.match(url)

    def _get_streams(self):
        match = self._url_re.match(self.url)
        video_id = match.group('video_id')

        if video_id is not None:
            # VOD
            res = http.get(self.VOD_API_URL.format(video_id))
            streams = http.json(res, schema=self._vod_api_schema)

            # Check whether video format is expired
            current_date = datetime.strptime(streams['current_date'], '%Y-%m-%dT%H:%M:%S.%f')
            valid_start = datetime.strptime(streams['shows'][0]['valid_start'], '%Y-%m-%dT%H:%M:%S')
            valid_end = datetime.strptime(streams['shows'][0]['valid_end'], '%Y-%m-%dT%H:%M:%S')
            if current_date < valid_start or current_date > valid_end:
                self.logger.error('Failed to access stream, may be due to expired content')
                return

            streams = streams['shows'][0]['media:group']

        else:
            # Live
            channel_id = match.group('channel_id')
            res = http.get(self.LIVE_API_URL.format(channel_id))
            streams = http.xml(res, schema=self._live_api_schema)

        for stream_url in streams:
            if '.f4m' in stream_url:
                for s in HDSStream.parse_manifest(self.session, stream_url).items():
                    yield s


__plugin__ = RTE
