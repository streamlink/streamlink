import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


class Mediaklikk(Plugin):
    PLAYER_URL = "https://player.mediaklikk.hu/playernew/player.php"

    _url_re = re.compile(r"https?://(?:www\.)?mediaklikk\.hu/[\w\-]+\-elo/?")
    _id_re = re.compile(r'"streamId":"(\w+)"')
    _file_re = re.compile(r'"file":\s*"([\w\./\\=:\-\?]+)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

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
        res = self.session.http.get(self.PLAYER_URL, params=params)
        m = self._file_re.search(res.text)
        if m:
            url = update_scheme("https://",
                                m.group(1).replace("\\/", "/"))

            log.debug("URL={0}".format(url))
            return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = Mediaklikk
