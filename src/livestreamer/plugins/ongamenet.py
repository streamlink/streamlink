from livestreamer.compat import str, bytes
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

import re

class Ongamenet(Plugin):
    PlayerURL = "http://www.ongamenet.com/front/ongame/live/vodPlayerHD.jsp"
    SWFURL = "http://www.ongamenet.com/front/ongame/live/CJPlayer.swf"
    PageURL = "http://www.ongamenet.com"
    Streams = {
        "high": "hd",
        "low": "sd"
    }

    @classmethod
    def can_handle_url(self, url):
        return "ongamenet.com" in url

    def _get_play_url(self, var):
        res = urlget(self.PlayerURL)

        stream = None
        server = None

        streams = re.findall(('var {0}Stream = "(.+)"\;\r\n').format(var), res.text)
        servers = re.findall(('var {0}Server = "(.+)"\;\r\n').format(var), res.text)

        if streams and len(streams) >= 2:
            stream = streams[1]

        if servers and len(servers) >= 1:
            server = servers[0]

        return (server, stream)

    def _get_streams(self):
        streams = {}

        for var, name in self.Streams.items():
            server, stream = self._get_play_url(var)

            if not (stream and server):
                continue

            streams[name] = RTMPStream(self.session, {
                "rtmp": server,
                "playpath": stream,
                "swfUrl": self.SWFURL,
                "pageUrl": self.PageURL,
                "live": True,
            })

        return streams

__plugin__ = Ongamenet
