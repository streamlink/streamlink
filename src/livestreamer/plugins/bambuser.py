from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HTTPStream, RTMPStream
from livestreamer.utils import verifyjson

import random
import re

PLAYER_URL = "http://player-c.api.bambuser.com/getVideo.json"

class Bambuser(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "bambuser.com/v/" in url

    def _get_streams(self):
        match = re.search("/v/(\d+)", self.url)
        if not match:
            return

        vid = match.group(1)
        params = dict(client_name="Bambuser AS2", context="b_broadcastpage",
                      raw_user_input=1, api_key="005f64509e19a868399060af746a00aa",
                      vid=vid, r=random.random())

        self.logger.debug("Fetching stream info")
        res = http.get(PLAYER_URL, params=params)
        json = http.json(res)

        error = json and json.get("errorCode")
        if error:
            error = error and json.get("error")
            self.logger.error(error)
            return

        json = verifyjson(json, "result")
        playpath = verifyjson(json, "id")
        url = verifyjson(json, "url")
        (width, height) = verifyjson(json, "size").split("x")
        name = "{0}p".format(height)

        parsed = urlparse(url)
        streams  = {}

        if parsed.scheme.startswith("rtmp"):
            if not RTMPStream.is_usable(self.session):
                raise PluginError("rtmpdump is not usable and required by Bambuser plugin")
            streams[name] = RTMPStream(self.session, {
                "rtmp": url,
                "playpath": playpath,
                "pageUrl": self.url,
                "live": True
            })
        elif parsed.scheme == "http":
            streams[name] = HTTPStream(self.session, url)

        return streams


__plugin__ = Bambuser
