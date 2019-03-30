import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class RTPPlay(Plugin):
    _url_re = re.compile(r"https?://www\.rtp\.pt/play/")
    _m3u8_re = re.compile(r"hls:(?:\s+)?(?:\'|\")(?P<url>[^\"']+)(?:\'|\")")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME,
                                          "Referer": self.url})
        res = self.session.http.get(self.url)
        m = self._m3u8_re.search(res.text)
        if not m:
            log.error("Could not find _m3u8_re")
            return

        hls_url = m.group("url")
        log.debug("Found URL: {0}".format(hls_url))
        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {"live": HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = RTPPlay
