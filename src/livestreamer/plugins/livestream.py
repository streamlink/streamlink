from livestreamer.compat import urljoin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import AkamaiHDStream
from livestreamer.utils import urlget, verifyjson, res_xml, parse_json

import re

class Livestream(Plugin):
    SWFURL = "http://cdn.livestream.com/swf/hdplayer-2.0.swf"

    @classmethod
    def can_handle_url(self, url):
        return "new.livestream.com" in url

    def _get_stream_info(self):
        res = urlget(self.url)

        match = re.search("initialData : ({.+})", res.text)

        if match:
            config = match.group(1)

            return parse_json(config, "config JSON")

    def _parse_smil(self, url):
        res = urlget(url)
        smil = res_xml(res, "SMIL config")

        streams = {}
        httpbase = smil.find("{http://www.w3.org/2001/SMIL20/Language}head/"
                             "{http://www.w3.org/2001/SMIL20/Language}meta[@name='httpBase']")

        if not (httpbase is not None and httpbase.attrib.get("content")):
            raise PluginError("Missing HTTP base in SMIL")

        httpbase = httpbase.attrib.get("content")

        videos = smil.findall("{http://www.w3.org/2001/SMIL20/Language}body/"
                              "{http://www.w3.org/2001/SMIL20/Language}switch/"
                              "{http://www.w3.org/2001/SMIL20/Language}video")

        for video in videos:
            url = urljoin(httpbase, video.attrib.get("src"))
            bitrate = int(video.attrib.get("system-bitrate"))
            streams[bitrate] = AkamaiHDStream(self.session, url,
                                              swf=self.SWFURL)

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
