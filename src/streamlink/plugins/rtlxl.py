import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, RTMPStream

_url_re = re.compile(r"http(?:s)?://(?:\w+\.)?rtl.nl/video/(?P<uuid>.*?)\Z", re.IGNORECASE)


class rtlxl(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        uuid = match.group("uuid")
        videourlfeed = http.get('https://tm-videourlfeed.rtl.nl/api/url/{}?device=pc&drm&format=hls'.format(uuid)).text

        videourlfeedjson = json.loads(videourlfeed)
        playlist_url = videourlfeedjson["url"]

        return HLSStream.parse_variant_playlist(self.session, playlist_url)


__plugin__ = rtlxl
