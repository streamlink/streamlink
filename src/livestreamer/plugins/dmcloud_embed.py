from livestreamer.plugin import Plugin
from livestreamer.utils import urlget

import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0"
}
URL_REGEX = r"http(s)?://api.dmcloud.net/player/embed/[\w\?=&\/;\-]+"
URLS = [
    r"http(s)?://(\w+\.)?action24.gr"
]


class DMCloudEmbed(Plugin):
    @classmethod
    def can_handle_url(self, url):
        for site in URLS:
            if re.match(site, url):
                return True

    def _get_streams(self):
        res = urlget(self.url, headers=HEADERS)

        match = re.search(URL_REGEX, res.text)
        if match:
            url = match.group(0)
            plugin = self.session.resolve_url(url)
            return plugin.get_streams()


__plugin__ = DMCloudEmbed
