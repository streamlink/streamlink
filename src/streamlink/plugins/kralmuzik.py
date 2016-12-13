from __future__ import print_function

import re

from streamlink.plugin.api import http
from streamlink.plugins.startv import StarTVBase


class KralMuzik(StarTVBase):
    url_re = re.compile(r"https?://www.kralmuzik.com.tr/tv/kral-tv")
    mobile_url_re = re.compile(r"(?P<quote>[\"'])(?P<url>https?://[^ ]*?/live/hls/[^ ]*?\?token=[^ ]*?)(?P=quote);")
    desktop_url_re = re.compile(r"(?P<quote>[\"'])(?P<url>https?://[^ ]*?/live/hds/[^ ]*?\?token=[^ ]*?)(?P=quote);")

    def _get_streams(self):
        res = http.get(self.url)
        mobile_match = self.mobile_url_re.search(res.text)
        desktop_match = self.desktop_url_re.search(res.text)

        mobile_url = mobile_match.group("url") if mobile_match else None
        desktop_url = desktop_match.group("url") if desktop_match else None

        return self._get_star_streams(desktop_url, mobile_url)


__plugin__ = KralMuzik
