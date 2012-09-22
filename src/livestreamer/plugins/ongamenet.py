from livestreamer.compat import str, bytes
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

import re

class Ongamenet(Plugin):
    PlayerURL = "http://www.tooniland.com/ongame/ognLive.tl"
    SWFURL = "http://www.ongamenet.com/front/ongame/live/CJPlayer.swf"
    PageURL = "http://www.ongamenet.com"
    Streams = ["sd", "hd"]

    @classmethod
    def can_handle_url(self, url):
        return "ongamenet.com" in url

    def _get_streams(self):
        res = urlget(self.PlayerURL)
        urls = re.findall("return \"(rtmp://.+)\"", res.text)
        streams = {}

        for i, url in enumerate(urls):
            if i >= len(self.Streams):
                name = "stream_" + str(i)
            else:
                name = self.Streams[i]

            streams[name] = RTMPStream(self.session, {
                "rtmp": url,
                "swfUrl": self.SWFURL,
                "pageUrl": self.PageURL,
                "live": True,
            })

        return streams

__plugin__ = Ongamenet
