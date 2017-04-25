import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http


_url_re = re.compile(r'''https?://cyro\.se/watch/''')
_embed_re = re.compile(r'''<iframe.+src="([^"]+)"''')


class Cyro(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _embed_re.search(res.text)
        if match:
            iframe_url = "https://cyro.se{0}".format(match.group(1))
            res = http.get(iframe_url)
            match = _embed_re.search(res.text)
            if match:
                iframe_url = "https://cyro.se{0}".format(match.group(1))
                res = http.get(iframe_url)
                match = _embed_re.search(res.text)
                if match:
                    url = match.group(1)
                    return self.session.streams(url)


__plugin__ = Cyro
