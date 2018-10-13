import re

from streamlink.plugin import Plugin
from streamlink.utils import update_scheme
from streamlink.plugins.theplatform import ThePlatform
from streamlink import NoStreamsError


class CWTV(Plugin):

    _url_re = re.compile(r"https?://(?:www\.)?cwtv\.com/shows/[\w-]+")
    _embed_re = re.compile(r"""iframe.+src="(?P<url>[^"]+theplatform[^"]+)""")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)

        try:
            theplatform_url = self._embed_re.search(res.text).group("url")
        except Exception:
            raise NoStreamsError(self.url)

        url = update_scheme(self.url, theplatform_url)
        p = ThePlatform(url)
        p.bind(self.session, "plugin.cwtv")
        return p.streams()


__plugin__ = CWTV
