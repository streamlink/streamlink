"""
$description Greek national live TV channels owned by The Hellenic Broadcasting Corporation.
$url ert.gr
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?ert.gr/",
))
class ERTTV(Plugin):
    def _get_streams(self):
        re_streams = re.compile(r"var\s*streamww\s*\=\s*\'(https:\/\/.*playlist_dvr\.m3u8*)\'")
        stream_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(re_streams.findall),
        ))[0]
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = ERTTV
