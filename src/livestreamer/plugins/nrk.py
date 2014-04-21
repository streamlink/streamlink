from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

import re

COOKIES = {
    'NRK_PLAYER_SETTINGS_TV': 'devicetype=desktop&preferred-player-odm=hlslink&preferred-player-live=hlslink'
}


class NRK(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return 'tv.nrk.no' in url

    def _get_streams(self):
        self.logger.debug('Extracting media URL')
        res = http.get(self.url, cookies=COOKIES)
        m = re.search(r'<div[^>]*?id="playerelement"[^>]+data-media="([^"]+)"',
                      res.text)
        if not m:
            return

        return HLSStream.parse_variant_playlist(self.session, m.group(1))

__plugin__ = NRK
