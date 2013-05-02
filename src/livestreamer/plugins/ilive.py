from livestreamer.compat import unquote
from livestreamer.stream import RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.utils import urlget

import re

class ILive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "ilive.to" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("flashplayer: \"(.+.swf)\".+streamer: \"(.+)\".+file: \"(.+).flv\"", res.text, re.DOTALL)
        if not match:
            raise NoStreamsError(self.url)

        rtmp = match.group(2)
        playpath = match.group(3)
        swfurl = match.group(1)


        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfVfy": swfurl,
            "playpath" : playpath,
            "live": True
        }, redirect=True)

        return streams


__plugin__ = ILive
