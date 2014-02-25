from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import HLSStream
from livestreamer.utils import urlget

import re

class NRK(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return 'tv.nrk.no' in url

    def _get_streams(self):
        self.logger.debug('Extracting media URL')
        res = urlget(self.url, cookies = {'NRK_PLAYER_SETTINGS_TV':
            'devicetype=desktop&preferred-player-odm=hlslink&preferred-player-live=hlslink'})
        m = re.search(r'<div[^>]*?id="playerelement"[^>]+data-media="([^"]+)"', res.text)
        if not m:
            raise NoStreamsError(self.url)
        return HLSStream.parse_variant_playlist(self.session, m.group(1))

__plugin__ = NRK
