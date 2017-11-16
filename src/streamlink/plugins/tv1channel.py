import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http

_url_re = re.compile(r'''https?://(www\.)?tv1channel\.org/''')
_embed_re = re.compile(r'''<iframe.+src="([^"]+)"''')


class TV1Channel(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _embed_re.search(res.text)

        if match:
            url = match.group(1)
            if url.startswith('//'):
                url = 'https:{0}'.format(url)
            return self.session.streams(url)


__plugin__ = TV1Channel
