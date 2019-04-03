import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


_stream_url_re = re.compile(r"http(s)?://(www\.)?mediaklikk.hu/[\w\-]+\-elo/?")
_id_re = re.compile(r'.*"streamId":"(\w+)".*')
_file_re = re.compile(r'.*"file": "([\w\./\\=:\-\?]+)".*')
_stream_player_url = "https://player.mediaklikk.hu/playernew/player.php?video={stream_id}&noflash=yes"


class Mediaklikk(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _stream_url_re.match(url)

    def _get_playlist_url(self):
        # get the stream id
        response = self.session.http.get(self.url)
        match = _id_re.search(response.text)
        if not match:
            raise ValueError("Stream ID couldn't be extracted from page, probably time to update the regex.")

        # get the m3u8 file url
        player_url = _stream_player_url.format(stream_id=match.group(1))
        response = self.session.http.get(player_url)

        match = _file_re.search(response.text)
        if match:
            url = match.group(1).replace("\\/", "/")
            if url.startswith("//"):
                url = "https:{}".format(url)

            return url

        raise ValueError("Couldn't extract m3u8 file URL, probably time to update the regex.")

    def _get_streams(self):
        playlist = self._get_playlist_url()
        return HLSStream.parse_variant_playlist(self.session, playlist)


__plugin__ = Mediaklikk
