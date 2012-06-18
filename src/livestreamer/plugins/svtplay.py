#!/usr/bin/env python

from livestreamer.compat import str
from livestreamer.plugins import Plugin, PluginError, NoStreamsError, register_plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, swfverify

import json, re


class SVTPlay(Plugin):
    JSONURL = "http://svtplay.se/live/{0}?output=json"
    SWFURL = "http://www.svtplay.se/public/swf/video/svtplayer-2012.15.swf"
    PageURL = "http://www.svtplay.se"

    @classmethod
    def can_handle_url(self, url):
        return "svtplay.se" in url

    def _get_channel_id(self, url):
        data = urlget(url)

        match = re.search(b'data-json-href="/live/(\d+)"', data)
        if match:
            return int(match.group(1))

    def _get_streams(self):
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)

        data = urlget(self.JSONURL.format(channelid))

        try:
            info = json.loads(str(data, "utf8"))
        except ValueError as err:
            raise PluginError(("Unable to parse JSON: {0})").format(err))

        if not ("video" in info and "videoReferences" in info["video"]):
            raise PluginError("Missing 'video' or 'videoReferences' key in JSON")

        streams = {}
        videos = info["video"]["videoReferences"]
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
