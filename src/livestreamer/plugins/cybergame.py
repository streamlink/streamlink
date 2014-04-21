from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream

import re

PLAYLIST_URL = "http://api.cybergame.tv/p/playlist.smil"
CONFIG_URL = "http://api.cybergame.tv/p/config.php"

class Cybergame(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "cybergame.tv" in url

    def _get_rtmp_streams(self, params, alternative=""):
        res = http.get(PLAYLIST_URL, params=params)
        root = http.xml(res)
        rtmp = root.find("./head/meta").attrib.get("base")
        if not rtmp:
            raise NoStreamsError(self.url)

        tmpsteams = {}

        videos = root.findall("./body/switch/video") or root.findall("./body/video")
        for video in videos:
            src = video.attrib.get("src")
            height = video.attrib.get("height")
            quality = "{0}p{1}".format(height, alternative)
            tmpsteams[quality] = RTMPStream(self.session, {
                "rtmp": "{0}/{1}".format(rtmp,src),
                "pageUrl": self.url,
                "live": True
            })

        return tmpsteams

    def _get_vod_streams(self):
        match = re.search("/videos/(\d+)", self.url)
        if not match:
            return
        params = dict(vod=match.group(1))
        return self._get_rtmp_streams(params)

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Cybergame plugin")

        if "/videos/" in self.url:
            return self._get_vod_streams()

        self.logger.debug("Fetching live stream info")
        res = http.get(self.url)

        match = re.search("channel=([^\"]+)", res.text)
        if not match:
            raise NoStreamsError(self.url)

        channelname = match.group(1)

        res = http.get(CONFIG_URL, params=dict(c=channelname, ports="y"))
        json = http.json(res)
        servers = json.get("servers")
        if not servers:
            raise NoStreamsError(self.url)

        alternative = ""
        streams  = {}

        for server in servers:
            srv, port = server.split(":")
            params = dict(channel=channelname, server=srv, port=port)
            tmpstreams = self._get_rtmp_streams(params, alternative)
            streams.update(tmpstreams)
            if not alternative:
                alternative = "_alt"
            else:
                break

        return streams


__plugin__ = Cybergame
