from livestreamer.compat import str
from livestreamer.plugins import Plugin, PluginError, NoStreamsError, register_plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, swfverify, verifyjson

import json, re


class SVTPlay(Plugin):
    JSONURL = "http://svtplay.se/live/{0}?output=json"
    SWFURL = "http://www.svtplay.se/public/swf/video/svtplayer-2012.15.swf"
    PageURL = "http://www.svtplay.se"

    @classmethod
    def can_handle_url(self, url):
        return "svtplay.se" in url

    def _get_channel_id(self, url):
        self.logger.debug("Fetching channel id")

        data = urlget(url)

        match = re.search(b'data-json-href="/live/(\d+)"', data)
        if match:
            return int(match.group(1))

    def _get_streams(self):
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)

        self.logger.debug("Fetching stream info")
        data = urlget(self.JSONURL.format(channelid))

        try:
            info = json.loads(str(data, "utf8"))
        except ValueError as err:
            raise PluginError(("Unable to parse JSON: {0})").format(err))

        streams = {}
        video = verifyjson(info, "video")
        videos = verifyjson(video, "videoReferences")

        self.logger.debug("Verifying SWF: {0}", self.SWFURL)
        swfhash, swfsize = swfverify(self.SWFURL)

        for video in videos:
            if not ("url" in video and "playerType" in video and video["playerType"] == "flash"):
                continue

            stream = RTMPStream({
                "rtmp": video["url"],
                "pageUrl": self.PageURL,
                "swfhash": swfhash,
                "swfsize": swfsize,
                "live": True
            })
            streams[str(video["bitrate"]) + "k"] = stream


        return streams

register_plugin("svtplay", SVTPlay)
