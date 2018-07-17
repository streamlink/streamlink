import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json


class RadioNet(Plugin):
    _url_re = re.compile(r"https?://(\w+)\.radio\.(net|at|de|dk|es|fr|it|pl|pt|se)")
    _stream_data_re = re.compile(r'\bstation\s*:\s*(\{.+\}),?\s*')

    _stream_schema = validate.Schema(
        validate.transform(_stream_data_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(parse_json),
                {
                    'stationType': validate.text,
                    'streamUrls': validate.all([{
                        'bitRate': int,
                        'streamUrl': validate.url()
                    }])
                },
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        streams = self.session.http.get(self.url, schema=self._stream_schema)
        if streams is None:
            return

        # Ignore non-radio streams (podcasts...)
        if streams['stationType'] != 'radio_station':
            return

        stream_urls = []
        for stream in streams['streamUrls']:
            if stream['streamUrl'] in stream_urls:
                continue

            if stream['bitRate'] > 0:
                bitrate = '{}k'.format(stream['bitRate'])
            else:
                bitrate = 'live'
            yield bitrate, HTTPStream(self.session, stream['streamUrl'])
            stream_urls.append(stream['streamUrl'])


__plugin__ = RadioNet
