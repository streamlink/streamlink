import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

EMBED_URL_1 = "http://www.canlitv.plus/kanallar.php?kanal={0}"
EMBED_URL_2 = "http://www.ecanlitvizle.net/embed.php?kanal={0}"

_m3u8_re = re.compile(r"""file\s*:\s*['"](?P<url>[^"']+)['"]""")
_url_re = re.compile(r"""http(s)?://(?:www\.)?(?P<domain>
    canlitv\.(com|plus)
    |
    canlitvlive\.(io|co|live|site)
    |
    ecanlitvizle\.net
    )
    /(izle/|(?:onizleme|tv)\.php\?kanal=)?
    (?P<channel>[\w\-\=]+)""", re.VERBOSE)


class Canlitv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")
        domain = match.group("domain")

        headers = {
            "Referer": self.url,
            "User-Agent": useragents.FIREFOX
        }

        if domain == "canlitv.plus":
            res = http.get(EMBED_URL_1.format(channel), headers=headers)
        elif domain == "ecanlitvizle.net":
            res = http.get(EMBED_URL_2.format(channel), headers=headers)
        else:
            res = http.get(self.url, headers=headers)

        url_match = _m3u8_re.search(res.text)

        if url_match:
            hls_url = url_match.group("url")

            if domain in ("canlitvlive.live", "canlitvlive.site"):
                 hls_url = "http:" + hls_url

            self.logger.debug("Found URL: {0}".format(hls_url))

            try:
                s = []
                for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                    yield s
                if not s:
                    yield "live", HLSStream(self.session, hls_url)
            except IOError as err:
                self.logger.error("Failed to extract streams: {0}", err)

__plugin__ = Canlitv
