from livestreamer.compat import unquote
from livestreamer.stream import RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.utils import urlget

import re

class ILive(Plugin):
    SWFURL = "http://cdn.static.ilive.to/jwplayer/player.swf"

    @classmethod
    def can_handle_url(self, url):
        return "ilive.to" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search(".+?flashvars=\"&streamer=(.+)?&file=(.+?).flv&.+?\"", res.text)
        if not match:
            raise NoStreamsError(self.url)

        rtmp = unquote(match.group(1))
        playpath = match.group(2)

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "playpath" : playpath,
            "live": True
        }, redirect=True)

        return streams


__plugin__ = ILive
