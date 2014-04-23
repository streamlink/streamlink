import re

from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream


class Furstream(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return re.match("^http(s)?://(\w+\.)?furstre\.am/stream.+", url)

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Furstream plugin")

        self.logger.debug("Fetching stream info")
        res = http.get(self.url)

        match = re.search("rtmp://(?:(?!\").)*", res.text)
        if match:
            self.logger.debug("Stream URL: " + match.group(0))
            rtmp = match.group(0)
        else:
            return

        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "live": True
        })

        return streams

__plugin__ = Furstream
