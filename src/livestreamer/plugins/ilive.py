from livestreamer.compat import urlparse
from livestreamer.stream import HLSStream, RTMPStream
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.exceptions import NoStreamsError

import re

MOBILE_URL = "http://www.ilive.to/m/channel.php"


class ILive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "ilive.to" in url

    def _get_streams(self):
        streams = {}
        try:
            streams = self._get_desktop_streams()
        except NoStreamsError:
            pass
        try:
            hlsstreams = self._get_mobile_streams()
            if hlsstreams:
                streams.update(hlsstreams)
        except IOError as err:
            self.logger.warning("Failed to get variant playlist: {0}", err)

        return streams

    def _get_mobile_streams(self):
        match = re.search("view/(\d+)", self.url)
        if not match:
            return

        res = http.get(MOBILE_URL, params=dict(n=match.group(1)))

        match = re.search("[^\"]+playlist.m3u8[^\"]+", res.content)
        if not match:
            return

        ios_url = match.group(0)
        ios_url = ios_url.replace("\\", "")

        return HLSStream.parse_variant_playlist(self.session, ios_url)

    def _get_desktop_streams(self):
        self.logger.debug("Fetching stream info")
        res = http.get(self.url)

        match = re.search("flashplayer: \"(.+.swf)\".+streamer: \"(.+)\""
                          ".+file: \"(.+).flv\"", res.text, re.DOTALL)
        if not match:
            raise NoStreamsError(self.url)

        rtmpurl = match.group(2).replace("\\/", "/")
        parsed = urlparse(rtmpurl)

        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        params = {
            "rtmp": rtmpurl,
            "app": app,
            "pageUrl": self.url,
            "swfVfy": match.group(1),
            "playpath" : match.group(3),
            "live": True
        }

        match = re.search("(http(s)?://.+/server.php\?id=\d+)",
                          res.text)
        if match:
            token_url = match.group(1)
            res = http.get(token_url, headers=dict(Referer=self.url))
            res = http.json(res)
            token = res.get("token")
            if token:
                params["token"] = token

        streams = {}
        streams["live"] = RTMPStream(self.session, params)

        return streams


__plugin__ = ILive
