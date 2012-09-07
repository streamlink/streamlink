from livestreamer.compat import str
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, swfverify, verifyjson

import re

class SVTPlay(Plugin):
    JSONURL = "http://svtplay.se/live/{0}"
    SWFURL = "http://www.svtplay.se/public/swf/video/svtplayer-2012.15.swf"
    PageURL = "http://www.svtplay.se"

    @classmethod
    def can_handle_url(self, url):
        return "svtplay.se" in url

    def _get_channel_id(self, url):
        self.logger.debug("Fetching channel id")

        res = urlget(url)


        match = re.search('data-json-href="/live/(\d+)"', res.text)
        if match:
            return int(match.group(1))

    def _get_streams(self):
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)

        self.logger.debug("Fetching stream info")
        res = urlget(self.JSONURL.format(channelid), params=dict(output="json"))

        if res.json is None:
            raise PluginError("No JSON data in stream info")

        streams = {}
        video = verifyjson(res.json, "video")
        videos = verifyjson(video, "videoReferences")

        self.logger.debug("Verifying SWF: {0}", self.SWFURL)
        swfhash, swfsize = swfverify(self.SWFURL)

        for video in videos:
            if not ("url" in video and "playerType" in video and video["playerType"] == "flash"):
                continue

            stream = RTMPStream(self.session, {
                "rtmp": video["url"],
                "pageUrl": self.PageURL,
                "swfhash": swfhash,
                "swfsize": swfsize,
                "live": True
            })
            streams[str(video["bitrate"]) + "k"] = stream

        return streams

__plugin__ = SVTPlay
