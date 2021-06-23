import json
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?rtl\.nl/video/(?P<uuid>.*?)\Z",
    re.IGNORECASE
))
class RTLxl(Plugin):
    def _get_streams(self):
        uuid = self.match.group("uuid")
        videourlfeed = self.session.http.get(
            'https://tm-videourlfeed.rtl.nl/api/url/{}?device=pc&drm&format=hls'.format(uuid)
        ).text

        videourlfeedjson = json.loads(videourlfeed)
        playlist_url = videourlfeedjson["url"]

        return HLSStream.parse_variant_playlist(self.session, playlist_url)


__plugin__ = RTLxl
