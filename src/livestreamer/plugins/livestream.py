import re

from collections import defaultdict

from livestreamer.compat import urljoin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import AkamaiHDStream, HLSStream
from livestreamer.utils import urlget, verifyjson, res_xml, parse_json


SWF_URL = "http://cdn.livestream.com/swf/hdplayer-2.0.swf"

class Livestream(Plugin):
    @classmethod
    def default_stream_types(cls, streams):
        return ["akamaihd", "hls"]

    @classmethod
    def can_handle_url(self, url):
        return "new.livestream.com" in url

    def _get_stream_info(self):
        res = urlget(self.url)
        match = re.search("window.config = ({.+})", res.text)
        if match:
            config = match.group(1)
            return parse_json(config, "config JSON")

    def _parse_smil(self, url, swfurl):
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
                                              swf=swfurl)

        return streams

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        info = self._get_stream_info()

        if not info:
            raise NoStreamsError(self.url)

        event = verifyjson(info, "event")
        streaminfo = verifyjson(event, "stream_info")

        if not streaminfo or not streaminfo.get("is_live"):
            raise NoStreamsError(self.url)

        streams = defaultdict(list)
        play_url = streaminfo.get("play_url")
        if play_url:
            swfurl = info.get("hdPlayerSwfUrl") or SWF_URL
            if not swfurl.startswith("http://"):
                swfurl = "http://" + swfurl

            qualities = streaminfo.get("qualities", [])
            smil = self._parse_smil(streaminfo["play_url"], swfurl)
            for bitrate, stream in smil.items():
                name = "{0}k".format(bitrate/1000)
                for quality in qualities:
                    if quality["bitrate"] == bitrate:
                        name = "{0}p".format(quality["height"])

                streams[name].append(stream)

        m3u8_url = streaminfo.get("m3u8_url")
        if m3u8_url:
            hls_streams = HLSStream.parse_variant_playlist(self.session,
                                                           m3u8_url,
                                                           namekey="pixels")
            for name, stream in hls_streams.items():
                streams[name].append(stream)

        return streams

__plugin__ = Livestream
