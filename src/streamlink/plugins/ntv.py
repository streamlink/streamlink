from __future__ import print_function

import re

from streamlink.plugin.api import http
from streamlink.plugins.startv import StarTVBase


class NTR(StarTVBase):
    """
    Support for live streams from http://www.ntv.com.tr/, very similar to StarTV
    """
    url_re = re.compile(r"https?://www.ntv.com.tr/canli-yayin/ntv")
    token_re = re.compile(r"data-player-token[ ]*=[ ]*(?P<quote>[\"'])(?P<token>.*?)(?P=quote)")
    player_src = re.compile(r"data-player-src[ ]*=[ ]*(?P<quote>[\"'])(?P<url>.*?)(?P=quote)")
    player_mobile_src = re.compile(r"data-player-mobile[ ]*=[ ]*(?P<quote>[\"'])(?P<url>.*?)(?P=quote)")

    def _get_streams(self):
        res = http.get(self.url)
        token_m = self.token_re.search(res.text)
        desktop_player_m = self.player_src.search(res.text)
        mobile_player_m = self.player_mobile_src.search(res.text)
        desktop_url, mobile_url = None, None

        if token_m and desktop_player_m:  # desktop stream
            desktop_url = desktop_player_m.group("url") + token_m.group("token")

        if token_m and mobile_player_m:  # mobile stream
            mobile_url = mobile_player_m.group("url") + token_m.group("token")

        return self._get_star_streams(desktop_url, mobile_url)


__plugin__ = NTR
