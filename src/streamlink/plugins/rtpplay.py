import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import HLSStream


class RTPPlay(Plugin):
    _url_re = re.compile(r"https?:\/\/www.rtp.pt\/play\/")
    _m3u8_re = re.compile(r"file:(?:\s+)?(?:\'|\")(?P<url>[^\"']+)(?:\'|\")")

    @classmethod
    def can_handle_url(cls, url):
        return RTPPlay._url_re.match(url)

    def _get_streams(self):

        headers = {
            "User-Agent": useragents.CHROME
        }

        res = http.get(self.url, headers=headers)

        url_match = RTPPlay._m3u8_re.search(res.text)

        if url_match:
            hls_url = url_match.group("url")

            self.logger.debug("Found URL: {0}".format(hls_url))

            try:
                s = []
                for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                    yield s
                if not s:
                    yield "live", HLSStream(self.session, hls_url)
            except IOError as err:
                self.logger.error("Failed to extract streams: {0}", err)


__plugin__ = RTPPlay
