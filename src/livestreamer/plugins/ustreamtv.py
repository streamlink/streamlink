#!/usr/bin/env python3

from livestreamer.plugins import Plugin, register_plugin
from livestreamer.utils import CommandLine
from livestreamer.compat import urllib, str, bytes

import xml.dom.minidom, re


class UStreamTV(Plugin):
    AMFURL = "http://cgw.ustream.tv/Viewer/getStream/1/{0}.amf"
    SWFURL = "http://cdn1.ustream.tv/swf/4/viewer.rsl.210.swf"

    @classmethod
    def can_handle_url(self, url):
        return "ustream.tv" in url

    def _get_channel_id(self, url):
        fd = urllib.urlopen(url)
        data = fd.read()
        fd.close()

        match = re.search(b"channelId=(\d+)", data)
        if match:
            return int(match.group(1))

    def get_streams(self):
        def get_amf_value(data, key):
            pattern = ("{0}\W\W\W(.+?)\x00").format(key)
            match = re.search(bytes(pattern, "ascii"), data)
            if match:
                return str(match.group(1), "ascii")

        channelid = self._get_channel_id(self.url)

        if not channelid:
            return False

        fd = urllib.urlopen(self.AMFURL.format(channelid))
        data = fd.read()
        fd.close()

        stream = {}

        playpath = get_amf_value(data, "streamName")
        cdnurl = get_amf_value(data, "cdnUrl")
        fmsurl = get_amf_value(data, "fmsUrl")

        if not playpath:
            return False

        stream["playpath"] = playpath
        stream["rtmp"] = cdnurl or fmsurl
        stream["url"] = self.url

        return {"live": stream}


    def stream_cmdline(self, stream, filename):
        cmd = CommandLine("rtmpdump")
        cmd.arg("rtmp", ("{0}/{1}").format(stream["rtmp"], stream["playpath"]))
        cmd.arg("swfUrl", self.SWFURL)
        cmd.arg("pageUrl", stream["url"])
        cmd.arg("live", True)
        cmd.arg("flv", filename)

        return cmd.format()


register_plugin("ustreamtv", UStreamTV)
