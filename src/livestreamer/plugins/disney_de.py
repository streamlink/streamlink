"""Plugin for Disney (Channel) Germany

Supports:
    - http://video.disney.de/sehen/*
    - http://disneychannel.de/sehen/*
    - http://disneychannel.de/livestream
"""

import re
import json

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?disney(channel)?.de/")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36"
}

# stream urls are in `Grill.burger`->stack->data->externals->data
_stream_hls_re = re.compile("\"hlsStreamUrl\":\s*(\"[^\"]+\")")
_stream_data_re = re.compile("\"dataUrl\":\s*(\"[^\"]+\")")


class DisneyDE(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        html = http.get(self.url, headers=HTTP_HEADERS).content

        url_match = _stream_hls_re.search(html)
        if url_match is None:
            url_match = _stream_data_re.search(html)

        stream_url = json.loads(url_match.group(1))

        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = DisneyDE
