from livestreamer.stream import RTMPStream
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.utils import urlget

import re

class Freedocast(Plugin):
    SWFURL = "http://cdn.freedocast.com/player-octo/yume/v5/infinite-hd-player-FREEDOCAST.SWF"
    PlayerURL = "http://www.freedocast.com/forms/watchstream.aspx?sc={0}"

    @classmethod
    def can_handle_url(self, url):
        return "freedocast.com" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("\"User_channelid\".+?value=\"(.+?)\"", res.text)
        if not match:
            raise NoStreamsError(self.url)

        headers = {
            "Referer": self.url
        }

        res = urlget(self.PlayerURL.format(match.group(1)), headers=headers)

        match = re.search("stream:\s+'(rtmp://.+?)'", res.text)
        if not match:
            raise NoStreamsError(self.url)

        rtmp = match.group(1)

        streams = {}

        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "live": True
            })

        return streams


__plugin__ = Freedocast
