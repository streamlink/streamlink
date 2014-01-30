from livestreamer.stream import RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.exceptions import NoStreamsError
from livestreamer.utils import urlget, res_json

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

        params = {
            "rtmp": match.group(2),
            "pageUrl": self.url,
            "swfVfy": match.group(1),
            "playpath" : match.group(3),
            "live": True
        }

        match = re.search("(http(s)?://.+/server.php\?id=\d+)",
                          res.text)
        if match:
            token_url = match.group(1)
            res = res_json(urlget(token_url, headers=dict(Referer=self.url)))
            token = res.get("token")
            if token:
                params["token"] = token

        streams = {}
        streams["live"] = RTMPStream(self.session, params)

        return streams


__plugin__ = ILive
