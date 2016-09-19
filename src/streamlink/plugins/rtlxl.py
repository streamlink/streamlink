import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, RTMPStream

_url_re = re.compile("""http(?:s)?://(?:\w+\.)?rtlxl.nl/#!/(?:.*)/(?P<uuid>.*?)\Z""", re.IGNORECASE)

class rtlxl(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        uuid = match.group("uuid")
        html = http.get('http://www.rtl.nl/system/s4m/vfd/version=2/uuid={}/d=pc/fmt=adaptive/'.format(uuid)).text

        playlist_url = "http://manifest.us.rtl.nl" + re.compile('videopath":"(?P<playlist_url>.*?)",', re.IGNORECASE).search(html).group("playlist_url")
        return HLSStream.parse_variant_playlist(self.session, playlist_url)

__plugin__ = rtlxl
