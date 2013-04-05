from livestreamer.compat import urlparse
from livestreamer.stream import RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.utils import urlget, res_json


class Owncast(Plugin):
    SWFURL = "http://www.owncast.me/player/player.swf"
    StreamInfoURL = "http://www.owncast.me/rtmp.php"

    @classmethod
    def can_handle_url(self, url):
        return "owncast.me" in url

    def _get_streams(self):
        channelid = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()

        self.logger.debug("Fetching stream info")
        headers = { "Referer" : self.url }
        options = dict(id=channelid)
        res = urlget(self.StreamInfoURL, headers=headers, params=options)
        json = res_json(res, "stream info JSON")

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        if not ("rtmp" in json and "streamname" in json):
            raise NoStreamsError(self.url)

        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Owncast plugin")

        rtmp = json["rtmp"]
        playpath = json["streamname"]

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfUrl": self.SWFURL,
            "playpath" : playpath,
            "live": True
        })

        return streams


__plugin__ = Owncast
