import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


class Mediaklikk(Plugin):
    DEFAULT_PLAYER_URL = "https://player.mediaklikk.hu/playernew/player.php"
    M4SPORT_PLAYER_URL = "https://m4sport.hu/playernew/player.php"

    _url_re = re.compile(r"https?://(?:www\.)?(?:mediaklikk|m4sport)\.hu/(?:elo/)?(?:[\w\-]+)?(live|-elo)?/?")
    _id_re = re.compile(r'"streamId":"(\w+)"')
    _default_file_re = re.compile(r'"file":\s*"([\w\./\\=:\-\?]+)"')
    # the m4sport site has multiple playlist item but it seems only the middle one with your own ip added works
    _m4sport_file_re = re.compile(r'"file":\s*"([\w\./\\=:\-\?]+)ip:.*"')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def is_m4sport(self):
        return "m4sport" in self.url

    @property
    def player_url(self):
        if self.is_m4sport:
            return self.M4SPORT_PLAYER_URL

        return self.DEFAULT_PLAYER_URL

    def get_playlist_url(self, content):
        if self.is_m4sport:
            m = self._m4sport_file_re.search(content)
        else:
            m = self._default_file_re.search(content)

        if not m:
            return None

        return update_scheme("https://", m.group(1).replace("\\/", "/"))

    def _get_streams(self):
        # get the stream id
        res = self.session.http.get(self.url)
        m = self._id_re.search(res.text)
        if not m:
            raise PluginError("Stream ID could not be extracted.")

        # get the m3u8 file url
        params = {
            "video": m.group(1),
            "noflash": "yes",
        }
        res = self.session.http.get(self.player_url, params=params)

        playlist_url = self.get_playlist_url(res.text)
        if playlist_url:
            log.debug("URL={0}".format(playlist_url))
            return HLSStream.parse_variant_playlist(self.session, playlist_url)


__plugin__ = Mediaklikk
