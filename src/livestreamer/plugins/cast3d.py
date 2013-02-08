from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HTTPStream
from livestreamer.utils import urlget

import re

class Cast3d(Plugin):
    SWFURL = "http://www.cast3d.biz/player.swf"
    PlayerURL = "http://www.cast3d.tv/embed.php"

    @classmethod
    def can_handle_url(self, url):
        return "cast3d.tv" in url

    def _get_streams(self):
        channelname = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()

        self.logger.debug("Fetching stream info")

        headers = {
            "Referer": self.url,
            "Accept-Encoding": "deflate"
        }

        options = dict(channel=channelname, vw="580", vh="390",
                       domain="www.cast3d.tv")

        res = urlget(self.PlayerURL, headers=headers, params=options)

        match = re.search(".+?'streamer':'(.+?)'", res.text)
        if not match:
            raise NoStreamsError(self.url)

        streams = {}
        url = urlparse(match.group(1))
        if url.scheme.startswith("rtmp"):
            redirect = False
            rtmp = match.group(1)
            if "redirect" in rtmp:
                redirect = True

            streams["live"] = RTMPStream(self.session, {
                "rtmp": rtmp,
                "pageUrl": self.url,
                "swfVfy": self.SWFURL,
                "playpath": channelname,
                "live": True
            }, redirect=redirect)

        elif url.scheme.startswith("http"):
            streams["live"] = HTTPStream(self.session, match.group(1))
        else:
            raise PluginError(("Invalid stream type: {0}").format(url.scheme))

        return streams


__plugin__ = Cast3d
