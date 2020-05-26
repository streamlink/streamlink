import re

from streamlink.plugin import Plugin
from streamlink.plugins.theplatform import ThePlatform
from streamlink.utils import update_scheme


class NBCSports(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?nbcsports\.com")
    embed_url_re = re.compile(r'''id\s*=\s*"vod-player".*?\ssrc\s*=\s*"(?P<url>.*?)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.embed_url_re.search(res.text)
        platform_url = m and m.group("url")

        if platform_url:
            url = update_scheme(self.url, platform_url)
            # hand off to ThePlatform plugin
            p = ThePlatform(url)
            p.bind(self.session, "plugin.nbcsports")
            return p.streams()


__plugin__ = NBCSports
