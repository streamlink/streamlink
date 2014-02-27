from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
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
        channelname = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()

        self.logger.debug("Fetching stream info")

        headers = {
            "Referer": self.url
        }

        res = urlget(self.PlayerURL.format(channelname), headers=headers)
        match = re.search("'FlashVars', '(id=\d+)&s=(.+?)&", res.text)
        if not match:
            raise NoStreamsError(self.url)

        channelname = "{0}?{1}".format(match.group(2), match.group(1))
        res = urlget(self.BalancerURL, headers=headers)

        match = re.search("redirect=(.+)", res.text)
        if not match:
            raise PluginError("Error retrieving RTMP address from loadbalancer")

        rtmp = match.group(1)
        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live/{1}".format(rtmp, channelname),
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "conn": "S:OK",
            "live": True
        })

        return streams


__plugin__ = Mips
