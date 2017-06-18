import re

from streamlink import NoPluginError
from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http


class ElLobo(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?ellobo106\.com/")
    iframe_re = re.compile(r'<iframe.*?src="([^"]+)".*?>.*?</iframe>', re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        # Search for the iframe in the page
        iframe_m = self.iframe_re.search(res.text)

        ustream_url = iframe_m and iframe_m.group(1)
        if ustream_url and "ott.streann.com" in ustream_url:
            try:
                return self.session.streams(ustream_url)
            except NoPluginError:
                raise PluginError("Could not play embedded stream: {0}".format(ustream_url))


__plugin__ = ElLobo
