import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http


_url_re = re.compile(r'''https?://(?:www\.)?teamliquid\.net/video/streams/''')
_afreecaRe = re.compile('View on Afreeca')
_twitchRe = re.compile('View on Twitch.tv')


class Teamliquid(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        
        afreeca=_afreecaRe.findall(res.text)
        twitch=_twitchRe.findall(res.text)

        if afreeca:
            streamAddressRe=re.compile('http://play.afreeca.com/[^">/]+')
            url=streamAddressRe.findall(res.text)[0]
            return self.session.streams(url)
        
        elif twitch:
            streamAddressRe=re.compile('http://www.twitch.tv/[^">/]+')
            url=streamAddressRe.findall(res.text)[0]
            return self.session.streams(url)
            
__plugin__ = Teamliquid
