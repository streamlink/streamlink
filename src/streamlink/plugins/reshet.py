from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugins.brightcove import BrightcovePlayer


class Reshet(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?reshet\.tv/(live|item/)")
    video_id_re = re.compile(r'"videoID"\s*:\s*"(\d+)"')
    account_id = "1551111274001"
    live_channel_id = "ref:stream_reshet_live1"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        bp = BrightcovePlayer(self.session, self.account_id)
        m = self.url_re.match(self.url)
        base = m and m.group(1)
        if base == "live":
            return bp.get_streams(self.live_channel_id)
        else:
            res = http.get(self.url)
            m = self.video_id_re.search(res.text)
            video_id = m and m.group(1)
            if video_id:
                return bp.get_streams(video_id)


__plugin__ = Reshet
