from livestreamer.compat import unquote
from livestreamer.stream import RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.exceptions import NoStreamsError

import re

class Aliez(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "aliez.tv" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = http.get(self.url)

        match = re.search("\"file\":[\t]+\"([^\"]+)\".+embedSWF\(\"([^\"]+)\"", res.text, re.DOTALL)
        if not match:
            raise NoStreamsError(self.url)

        rtmp = unquote(match.group(1))
        swfurl = match.group(2)

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfVfy": swfurl,
            "live": True
        }, redirect=True)

        return streams

__plugin__ = Aliez
