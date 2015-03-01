"""Plugin for Disney (Channel) Germany

Supports:
    - http://video.disney.de/sehen/*
    - http://disneychannel.de/sehen/*
    - http://disneychannel.de/livestream
"""

import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.plugin.api.utils import parse_json
from livestreamer.stream import HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?disney(channel)?.de/")

# stream urls are in `Grill.burger`->stack->data->externals->data
_stream_hls_re = re.compile("\"hlsStreamUrl\":\s*(\"[^\"]+\")")
_stream_data_re = re.compile("\"dataUrl\":\s*(\"[^\"]+\")")


class DisneyDE(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = (_stream_hls_re.search(res.text) or
                 _stream_data_re.search(res.text))
        if not match:
            return

        stream_url = parse_json(match.group(1))

        return HLSStream.parse_variant_playlist(self.session, stream_url)

__plugin__ = DisneyDE
