import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugins.theplatform import ThePlatform
from streamlink.utils.url import update_scheme


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?nbcsports\.com"
))
class NBCSports(Plugin):
    embed_url_re = re.compile(r'''id\s*=\s*"vod-player".*?\ssrc\s*=\s*"(?P<url>.*?)"''')

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.embed_url_re.search(res.text)
        platform_url = m and m.group("url")

        if platform_url:
            url = update_scheme("https://", platform_url)
            # hand off to ThePlatform plugin
            p = ThePlatform(url)
            p.bind(self.session, "plugin.nbcsports")
            return p.streams()


__plugin__ = NBCSports
