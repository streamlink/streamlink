import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Bigo(Plugin):
    _url_re = re.compile(r"^https?://(?:www\.)?bigo\.tv/[^/]+$")
    _video_re = re.compile(
        r"""videoSrc:\s?["'](?P<url>[^"']+)["']""",
        re.M)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        page = http.get(self.url,
                        allow_redirects=True,
                        headers={"User-Agent": useragents.IPHONE_6})
        videomatch = self._video_re.search(page.text)
        if not videomatch:
            log.error("No playlist found.")
            return

        videourl = videomatch.group(1)
        log.debug("URL={0}".format(videourl))
        yield "live", HLSStream(self.session, videourl)


__plugin__ = Bigo
