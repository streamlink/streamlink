import re

from requests.adapters import HTTPAdapter

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

GOODGAME_URL_FORMAT = "http://hls.goodgame.ru/hls/{0}.m3u8"
GOODGAME_URL_FORMAT_720 = "http://hls.goodgame.ru/hls/{0}_720.m3u8"
GOODGAME_URL_FORMAT_480 = "http://hls.goodgame.ru/hls/{0}_480.m3u8"
GOODGAME_URL_FORMAT_240 = "http://hls.goodgame.ru/hls/{0}_240.m3u8"

_url_re = re.compile("http://(?:www\.)?goodgame.ru/channel/(?P<user>\w+)/")

class GoodGame(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        res = http.get(self.url)
        match = re.search("                    data-objid=\"(\d+)\" id=\"channel-popup-link\" class=\"fright font-size-small\">", res.text)
        print(match)
        theurl = GOODGAME_URL_FORMAT.format(match.group(1))
        
        streams = {}
        
        streams["1080p"] = HLSStream(self.session, GOODGAME_URL_FORMAT.format(match.group(1)))
        streams["720p"] = HLSStream(self.session, GOODGAME_URL_FORMAT_720.format(match.group(1)))
        streams["480p"] = HLSStream(self.session, GOODGAME_URL_FORMAT_480.format(match.group(1)))
        streams["240p"] = HLSStream(self.session, GOODGAME_URL_FORMAT_240.format(match.group(1)))
        
        return streams

__plugin__ = GoodGame
