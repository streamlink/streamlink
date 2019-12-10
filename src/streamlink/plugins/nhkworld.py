"""Plugin for NHK World, NHK Japan's english TV channel."""

import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

API_URL = "http://{}.nhk.or.jp/nhkworld/app/tv/hlslive_web.json"

_url_re = re.compile(r"http(?:s)?://(?:(\w+)\.)?nhk.or.jp/nhkworld")


class NHKWorld(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    def _get_streams(self):
        # get the HLS json from the same sub domain as the main url, defaulting to www
        sdomain = _url_re.match(self.url).group(1) or "www"
        res = self.session.http.get(API_URL.format(sdomain))

        stream_url = self.session.http.json(res)['main']['wstrm']
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = NHKWorld
