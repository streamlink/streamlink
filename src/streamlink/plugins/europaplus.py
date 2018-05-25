from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream


class EuropaPlusTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?europaplus\.ru/europaplustv")
    src_re = re.compile(r"""['"]file['"]\s*:\s*(?P<quote>['"])(?P<url>.*?)(?P=quote)""")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        for iframe in itertags(res.text, "iframe"):
            self.logger.debug("Found iframe: {0}".format(iframe))
            iframe_res = http.get(iframe.attributes['src'], headers={"Referer": self.url})
            m = self.src_re.search(iframe_res.text)
            surl = m and m.group("url")
            if surl:
                self.logger.debug("Found stream URL: {0}".format(surl))
                return HLSStream.parse_variant_playlist(self.session, surl)


__plugin__ = EuropaPlusTV
