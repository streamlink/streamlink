import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) "
                   "Gecko/20100101 Firefox/25.0")
}
URLS = [
    re.compile("http(s)?://(\w+\.)?action24.gr")
]

_embed_re = re.compile("http(s)?://api.dmcloud.net/player/embed/[\w\?=&\/;\-]+")


class DMCloudEmbed(Plugin):
    @classmethod
    def can_handle_url(self, url):
        for site in URLS:
            if site.match(url):
                return True

    def _get_streams(self):
        res = http.get(self.url, headers=HEADERS)

        match = _embed_re.search(res.text)
        if match:
            url = match.group(0)
            return self.session.streams(url)


__plugin__ = DMCloudEmbed
