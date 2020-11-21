import logging
import re
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


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
                        'url': validate.url(),
                        'contentFormat': validate.text,
                    }])
                },
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        streams = self.session.http.get(self.url, schema=self._stream_schema)
        if streams is None:
            return

        if streams['type'] != 'STATION':
            return

        stream_urls = set()
        for stream in streams['streams']:
            log.trace('{0!r}'.format(stream))
            url = stream['url']

            url_no_scheme = urlunparse(urlparse(url)._replace(scheme=''))
            if url_no_scheme in stream_urls:
                continue
            stream_urls.add(url_no_scheme)

            if stream['contentFormat'] in ('audio/mpeg', 'audio/aac'):
                yield 'live', HTTPStream(self.session, url, allow_redirects=True)
            elif stream['contentFormat'] == 'video/MP2T':
                streams = HLSStream.parse_variant_playlist(self.session, stream["url"])
                if not streams:
                    yield stream["quality"], HLSStream(self.session, stream["url"])
                else:
                    yield from streams.items()


__plugin__ = RadioNet
