import re

from streamlink import streams
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.utils import update_scheme


class NBC(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?nbc\.com")
    embed_url_re = re.compile(r'''(?P<q>["'])embedURL(?P=q)\s*:\s*(?P<q2>["'])(?P<url>.*?)(?P=q2)''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        m = self.embed_url_re.search(res.text)
        platform_url = m and m.group("url")

        if platform_url:
            # hand off to ThePlatform plugin
            return streams(update_scheme(self.url, platform_url))


__plugin__ = NBC
