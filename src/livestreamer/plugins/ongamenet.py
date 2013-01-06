from livestreamer.compat import str, bytes
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

import re

class Ongamenet(Plugin):
    PlayerURL = "http://dostream.lab.so/stream.php?from=ongamenet"
    SWFURL = "http://www.ongamenet.com/front/ongame/live/CJPlayer.swf"
    PageURL = "http://www.ongamenet.com"

    @classmethod
    def can_handle_url(self, url):
        return "ongamenet.com" in url

    def _get_streams(self):
        res = urlget(self.PlayerURL)

        match = re.search("var stream = \"(.+?)\";", res.text)
        if not match:
            raise NoStreamsError(self.url)

        stream = match.group(1)

        match = re.search("var server = \"(.+?)\";", res.text)
        if not match:
            raise NoStreamsError(self.url)

        server = match.group(1)

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": server,
            "playpath": stream,
            "swfUrl": self.SWFURL,
            "pageUrl": self.PageURL,
            "live": True,
        })

        return streams

__plugin__ = Ongamenet
