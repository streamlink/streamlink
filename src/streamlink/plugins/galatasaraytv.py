import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class GalatasarayTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?galatasaray\.com")
    playervars_re = re.compile(r"sources\s*:\s*\[\s*\{\s*type\s*:\s*\"(.*?)\",\s*src\s*:\s*\"(.*?)\"", re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_title(self):
        return "Galatasaray TV"

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self.playervars_re.search(res.text)
        if match:
            stream_url = match.group(2)
            log.debug("URL={0}".format(stream_url))
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = GalatasarayTV
