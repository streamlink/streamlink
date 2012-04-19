#!/usr/bin/env python3

from livestreamer.plugins import Plugin, register_plugin
from livestreamer.stream import RTMPStream
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

    def _get_streams(self):
        def get_amf_value(data, key):
            pattern = ("{0}\x02\x00.(.+?)\x00").format(key)
            match = re.search(bytes(pattern, "ascii"), data)
            if match:
                return str(match.group(1), "ascii")

        channelid = self._get_channel_id(self.url)

        if not channelid:
            return False

        fd = urllib.urlopen(self.AMFURL.format(channelid))
        data = fd.read()
        fd.close()

        playpath = get_amf_value(data, "streamName")
        cdnurl = get_amf_value(data, "cdnUrl")
        fmsurl = get_amf_value(data, "fmsUrl")

        if not playpath:
            return False

        stream = RTMPStream({
            "rtmp": ("{0}/{1}").format(cdnurl or fmsurl, playpath),
            "pageUrl": self.url,
            "swfUrl": self.SWFURL,
            "live": 1
        })

        return {"live": stream}

register_plugin("ustreamtv", UStreamTV)
