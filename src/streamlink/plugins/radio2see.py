import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugins.livestream import Livestream

class Radio2See(Livestream):
    """
    Support for www.radio21.de/tv & www.rockland.de/tv Live TV stream
    """
    _url_re = re.compile(r"https?://(?:www)\.(?:(radio21|rockland))\.de/(?:musik/)?(?:tv)")
    _streamsrc_re = re.compile(r"""<iframe.+?src=["'](?P<streamsrc>[^"']+)["']""", re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        headers = {
            'User-Agent': useragents.CHROME,
        }

        res  = http.get(self.url, headers=headers)
        src_m = self._streamsrc_re.search(res.text) 
        if src_m:
            self.url = src_m.group("streamsrc")
            return Livestream._get_streams(self)
        else:
            self.logger.error(u"Could not find the Livestream source for Radio2See")

__plugin__ = Radio2See