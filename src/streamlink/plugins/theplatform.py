import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class ThePlatform(Plugin):
    """
    Plugin to support streaming videos hosted by thePlatform
    """
    url_re = re.compile(r"https?://player.theplatform.com/p/")
    release_re = re.compile(r'''tp:releaseUrl\s*=\s*"(.*?)"''')
    video_src_re = re.compile(r'''video.*?src="(.*?)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

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
                self.logger.error("{0}: {1}",
                                  error.get("title", "Error"),
                                  error.get("description", "An unknown error occurred"))


__plugin__ = ThePlatform
