import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://player\.theplatform\.com/p/"
))
class ThePlatform(Plugin):
    release_re = re.compile(r'''tp:releaseUrl\s*=\s*"(.*?)"''')
    video_src_re = re.compile(r'''video.*?src="(.*?)"''')

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.release_re.search(res.text)
        release_url = m and m.group(1)
        if release_url:
            api_url = release_url + "&formats=m3u,mpeg4"
            res = self.session.http.get(api_url, allow_redirects=False, raise_for_status=False)
            if res.status_code == 302:
                stream_url = res.headers.get("Location")
                return HLSStream.parse_variant_playlist(self.session, stream_url, headers={
                    "Referer": self.url
                })
            else:
                error = self.session.http.json(res)
                log.error("{0}: {1}".format(
                    error.get("title", "Error"),
                    error.get("description", "An unknown error occurred")
                ))


__plugin__ = ThePlatform
