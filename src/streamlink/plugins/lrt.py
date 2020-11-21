import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class LRT(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?lrt.lt/mediateka/tiesiogiai/.")
    _video_id_re = re.compile(r"""var\svideo_id\s*=\s*["'](?P<video_id>\w+)["']""")
    API_URL = "https://www.lrt.lt/servisai/stream_url/live/get_live_url.php?channel={0}"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        page = self.session.http.get(self.url)
        m = self._video_id_re.search(page.text)
        if m:
            video_id = m.group("video_id")
            data = self.session.http.get(self.API_URL.format(video_id)).json()
            hls_url = data["response"]["data"]["content"]

            yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()
        else:
            log.debug("No match for video_id regex")


__plugin__ = LRT
