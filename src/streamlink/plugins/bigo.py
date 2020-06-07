import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Bigo(Plugin):
    _url_re = re.compile(r"^https?://(?:www\.)?bigo\.tv/[^/]+$")
    _video_re = re.compile(
        r"""videoSrc:\s?["'](?P<url>[^"']+)["']""",
        re.M)
    api_url = "http://www.bigo.tv/OInterface/getVideoParam?bigoId="

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        extract_id = self.url.split('/')[-1]
        page = self.session.http.get(
            self.api_url + extract_id,
            allow_redirects=True,
            headers={"User-Agent": useragents.IPHONE_6}
        )
        videomatch = page.json()['data']['videoSrc']
        if not videomatch:
            log.error("No playlist found.")
            return

        videourl = videomatch
        log.debug("URL={0}".format(videourl))
        yield "live", HLSStream(self.session, videourl)


__plugin__ = Bigo
