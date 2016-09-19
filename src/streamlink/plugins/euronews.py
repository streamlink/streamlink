import re

from itertools import chain

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream, HTTPStream

from streamlink.plugin.api.support_plugin import common_jwplayer as jwplayer

_url_re = re.compile("http(s)?://(\w+\.)?euronews.com")


class Euronews(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _create_stream(self, source):
        url = source["file"]

        if urlparse(url).path.endswith("m3u8"):
            streams = HLSStream.parse_variant_playlist(self.session, url)

            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in streams.items():
                yield stream
        else:
            name = source.get("label", "vod")
            yield name, HTTPStream(self.session, url)

    def _get_streams(self):
        res = http.get(self.url)
        playlist = jwplayer.parse_playlist(res)
        if not playlist:
            return

        for item in playlist:
            streams = map(self._create_stream, item["sources"])

            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in chain.from_iterable(streams):
                yield stream

__plugin__ = Euronews
