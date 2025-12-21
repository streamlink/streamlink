import re
import logging

from streamlink.plugin import Plugin, pluginmatcher, PluginError
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

@pluginmatcher(
    name="taratata",
    pattern=re.compile(r"https?://(?:www\.)?mytaratata\.com/taratata/\d+/"),
)
class Taratata(Plugin):

    def _get_video_page_url(self):
        """
        Extract data-url='https://mytaratata.com/videos/{id}'
        (accepts single or double quotes)
        """
        html = self.session.http.get(self.url).text

        m = re.search(
            r"data-url=['\"]([^'\"]+/videos/\d+)['\"]",
            html
        )
        if not m:
            raise PluginError("Unable to find Taratata video page URL (data-url)")

        return m.group(1)

    def _get_streams(self):
        log.debug("Resolving Taratata streams")

        hls_url = self._get_video_page_url()
        if hls_url is not None:
            return HLSStream.parse_variant_playlist(self.session, hls_url)

__plugin__ = Taratata
