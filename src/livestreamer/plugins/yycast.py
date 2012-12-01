from livestreamer.stream import RTMPStream
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.utils import urlget

import re

class YYCast(Plugin):
    SWFURL = "http://cdn.yycast.com/player/player.swf"

    @classmethod
    def can_handle_url(self, url):
        return "yycast.com" in url

    def _get_streams(self):
        playpath = self.url.rstrip("/").rpartition("/")[2].lower()

        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("'streamer':\s+'(.+?)'", res.text)
        if not match:
            raise NoStreamsError(self.url)
 
        rtmp = match.group(1)

        streams = {}

        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "playpath" : playpath,
            "live": True
            }, redirect=True)

        return streams


__plugin__ = YYCast
