import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http


_url_re = re.compile("http(s)?://(www\.)?tv(3|6|8|10)\.se")
_embed_re = re.compile('<iframe class="iframe-player" src="([^"]+)">')


class ViasatEmbed(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)

        match = _embed_re.search(res.text)
        if match:
            url = match.group(1)
            return self.session.streams(url)


__plugin__ = ViasatEmbed
