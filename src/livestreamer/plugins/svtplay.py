import re

from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream, HLSStream, HDSStream
from livestreamer.utils import verifyjson

SWF_URL = "http://www.svtplay.se/public/swf/video/svtplayer-2012.15.swf"
PAGE_URL = "http://www.svtplay.se"


class SVTPlay(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match("http(s)?://(www\.)?(svtplay|svtflow|oppetarkiv).se/", url)

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = http.get(self.url, params=dict(output="json"))
        json = http.json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")

        streams = {}
        video = verifyjson(json, "video")
        videos = verifyjson(video, "videoReferences")

        for video in videos:
            if not ("url" in video and "playerType" in video):
                continue

            url = video["url"]

            if video["playerType"] == "flash":
                if url.startswith("rtmp"):
                    stream = RTMPStream(self.session, {
                        "rtmp": url,
                        "pageUrl": PAGE_URL,
                        "swfVfy": SWF_URL,
                        "live": True
                    })
                    streams[str(video["bitrate"]) + "k"] = stream
                elif "manifest.f4m" in url:
                    try:
                        hdsstreams = HDSStream.parse_manifest(self.session, url)
                        streams.update(hdsstreams)
                    except IOError as err:
                        self.logger.warning("Failed to get HDS manifest: {0}", err)

            elif video["playerType"] == "ios":
                try:
                    hlsstreams = HLSStream.parse_variant_playlist(self.session, url)
                    streams.update(hlsstreams)
                except IOError as err:
                    self.logger.warning("Failed to get variant playlist: {0}", err)

        return streams

__plugin__ = SVTPlay
