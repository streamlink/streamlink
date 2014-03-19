from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import HLSStream
from livestreamer.plugin.api import http

import re

class Chaturbate(Plugin):
    _reSrc = re.compile(r'html \+= \"src=\'([^\']+)\'\";')
    
    @classmethod
    def can_handle_url(self, url):
        return "chaturbate.com" in url

    def _get_streams(self):
        res = http.get(self.url)
        match = self._reSrc.search(res.text)
        if not match:
            raise NoStreamsError(self.url)
        return HLSStream.parse_variant_playlist(self.session, match.group(1))
        
__plugin__ = Chaturbate
