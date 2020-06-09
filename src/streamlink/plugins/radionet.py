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
                    'type': validate.text,
                    'streams': validate.all([{
                        'url': validate.url()
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
        if streams['type'] != 'STATION':
            return

        stream_urls = []
        for stream in streams['streams']:
            url = stream['url']
            if url in stream_urls:
                continue

            # NOTE there doesn't appear to be any bit rate information any
            # more so I hard code it to 'live':
            bitrate = 'live'
            yield bitrate, HTTPStream(self.session, url)
            stream_urls.append(url)


__plugin__ = RadioNet
