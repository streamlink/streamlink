from livestreamer.compat import str
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream, HLSStream
from livestreamer.utils import urlget, verifyjson, res_json

import re

class SVTPlay(Plugin):
    SWFURL = "http://www.svtplay.se/public/swf/video/svtplayer-2012.15.swf"
    PageURL = "http://www.svtplay.se"

    @classmethod
    def can_handle_url(self, url):
        return "svtplay.se" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url, params=dict(output="json"))
        json = res_json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        streams = {}
        video = verifyjson(json, "video")
        videos = verifyjson(video, "videoReferences")

        for video in videos:
            if not ("url" in video and "playerType" in video):
                continue

            if video["playerType"] == "flash":
                if video["url"].startswith("rtmp"):
                    stream = RTMPStream(self.session, {
                        "rtmp": video["url"],
                        "pageUrl": self.PageURL,
                        "swfVfy": self.SWFURL,
                        "live": True
                    })
                    streams[str(video["bitrate"]) + "k"] = stream
            elif video["playerType"] == "ios":
                try:
                    hlsstreams = HLSStream.parse_variant_playlist(self.session, video["url"])
                    streams.update(hlsstreams)
                except IOError as err:
                    self.logger.warning("Failed to get variant playlist: {0}", err)

        return streams

__plugin__ = SVTPlay
