from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import AkamaiHDStream
from livestreamer.utils import urlget, verifyjson, res_xml, parse_json

import json
import re

class Livestream(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "new.livestream.com" in url

    def _get_stream_info(self):
        res = urlget(self.url)

        match = re.search("var initialData = ({.+})", res.text)

        if match:
            config = match.group(1)

            return parse_json(config, "config JSON")

    def _parse_smil(self, url):
        res = urlget(url)
        dom = res_xml(res, "config XML")

        httpbase = None
        streams = {}

        for meta in dom.getElementsByTagName("meta"):
            if meta.getAttribute("name") == "httpBase":
                httpbase = meta.getAttribute("content")
                break

        if not httpbase:
            raise PluginError("Missing HTTP base in SMIL")

        for video in dom.getElementsByTagName("video"):
            url = "{0}/{1}".format(httpbase, video.getAttribute("src"))
            bitrate = int(video.getAttribute("system-bitrate"))
            streams[bitrate] = AkamaiHDStream(self.session, url)

        return streams

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        info = self._get_stream_info()

        if not info:
            raise NoStreamsError(self.url)

        streaminfo = verifyjson(info, "stream_info")

        if not streaminfo:
            raise NoStreamsError(self.url)

        qualities = verifyjson(streaminfo, "qualities")

        streams = {}

        if not streaminfo["is_live"]:
            raise NoStreamsError(self.url)

        if "play_url" in streaminfo:
            smil = self._parse_smil(streaminfo["play_url"])

            for bitrate, stream in smil.items():
                sname = "{0}k".format(bitrate/1000)

                for quality in qualities:
                    if quality["bitrate"] == bitrate:
                        sname = "{0}p".format(quality["height"])

                streams[sname] = stream

        return streams


__plugin__ = Livestream
