from livestreamer.stream import RTMPStream
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.utils import urlget

import re

class Mips(Plugin):
    SWFURL = "http://mips.tv/content/scripts/eplayer.swf"
    PlayerURL = "http://mips.tv/embedplayer/{0}/1/500/400"
    BalancerURL = "http://www.mips.tv:1935/loadbalancer"

    @classmethod
    def can_handle_url(self, url):
        return "mips.tv" in url

    def _get_streams(self):
        channelname = self.url.rstrip("/").rpartition("/")[2].lower()

        self.logger.debug("Fetching stream info")

        headers = {
            "Referer": self.url
        }

        res = urlget(self.PlayerURL.format(channelname), headers=headers)

        match = re.search("'FlashVars', '(id=\d+)&", res.text)
        if not match:
            raise NoStreamsError(self.url)

        channelname += "?" + match.group(1)

        res = urlget(self.BalancerURL, headers=headers)

        match = re.search("redirect=(.+)", res.text)
        if not match:
            raise PluginError("Error retrieving rtmp address from loadbalancer")

        rtmp = match.group(1)

        streams = {}

        streams["live"] = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live/{1}".format(rtmp, channelname),
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "live": True
            })

        return streams


__plugin__ = Mips
