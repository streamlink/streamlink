"""
$description Global and country-specific websites for live radio simulcasts for over 40,000 stations.
$url radio.net
$url radio.at
$url radio.de
$url radio.dk
$url radio.es
$url radio.fr
$url radio.it
$url radio.pl
$url radio.pt
$url radio.se
$type live
"""

import logging
import re
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(\w+)\.radio\.(net|at|de|dk|es|fr|it|pl|pt|se)"
))
class RadioNet(Plugin):
    def _get_streams(self):
        streams = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"\bstation\s*:\s*(\{.+}),?\s*"),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                {
                    "type": str,
                    "streams": [{
                        "url": validate.url(),
                        "contentFormat": str,
                    }],
                },
            ),
        ))
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
