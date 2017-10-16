from __future__ import print_function
import re

from streamlink import streams
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate


class StarTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?startv.com.tr/canli-yayin")
    iframe_re = re.compile(r'frame .*?src="(https://www.youtube.com/[^"]+)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        m = self.iframe_re.search(res.text)

        yt_url = m and m.group(1)
        if yt_url:
            self.logger.debug("Deferring to YouTube plugin with URL: {0}".format(yt_url))
            return streams(yt_url)


__plugin__ = StarTV
