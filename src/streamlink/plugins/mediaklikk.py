import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.plugin.api import http


_stream_url_re = re.compile(r"http(s)?://(www\.)?mediaklikk.hu/([A-Za-z0-9\-]+)/?")
_id_re = re.compile(r'.*data\-streamid="([a-z0-9]+)".*')
_file_re = re.compile(r'.*{\'file\': ?\'([a-zA-Z0-9\./\?=:]+)\'}].*')

_stream_player_url = "http://player.mediaklikk.hu/player/player-inside-full3.php?userid=mtva&streamid={0}&flashmajor=21&flashminor=0"


class Mediaklikk(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _stream_url_re.match(url)

    def _get_playlist_url(self):
        # get the id
        content = http.get(self.url)
        match = _id_re.match(content.text.replace("\n", ""))
        if not match:
            return

        # get the m3u8 file url
        player_url = _stream_player_url.format(match.group(1))
        content = http.get(player_url)

        match = _file_re.match(content.text.replace("\n", ""))
        if match:
            return match.group(1)

    def _get_streams(self):
        playlist = self._get_playlist_url()
        return HLSStream.parse_variant_playlist(self.session, playlist)


__plugin__ = Mediaklikk
