import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream

_RE_URL = re.compile(r'^https?://(?:www.)stream.me/(\w+).*$')


class StreamMe(Plugin):

    @classmethod
    def can_handle_url(cls, url):
        return bool(_RE_URL.match(url))

    def _get_streams(self):
        username = _RE_URL.match(self.url).group(1)
        url = 'https://www.stream.me/api-user/v1/{}/channel'.format(username)
        data = http.get(url).json()
        try:
            m3u8 = data['_embedded']['streams'][0]['_links']['hlsmp4']['href']
            return HLSStream.parse_variant_playlist(self.session, m3u8)
        except KeyError:
            return {}

__plugin__ = StreamMe
