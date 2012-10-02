from livestreamer.compat import str, bytes
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

import xml.dom.minidom, re

class UStreamTV(Plugin):
    AMFURL = "http://cgw.ustream.tv/Viewer/getStream/1/{0}.amf"
    SWFURL = "http://cdn1.ustream.tv/swf/4/viewer.rsl.210.swf"

    @classmethod
    def can_handle_url(self, url):
        return "ustream.tv" in url

    def _get_channel_id(self, url):
        res = urlget(url)

        match = re.search("\"cid\":(\d+)", res.text)
        if match:
            return int(match.group(1))

    def _get_streams(self):
        def get_amf_value(data, key):
            pattern = ("{0}\x02..(.*?)\x00").format(key)
            match = re.search(bytes(pattern, "ascii"), data)
            if match:
                return str(match.group(1), "ascii")

        streams = {}
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)

        self.logger.debug("Fetching stream info")
        res = urlget(self.AMFURL.format(channelid))
        data = res.content

        playpath = get_amf_value(data, "streamName")
        cdnurl = get_amf_value(data, "cdnUrl")
        fmsurl = get_amf_value(data, "fmsUrl")

        if playpath:
            stream = RTMPStream(self.session, {
                "rtmp": ("{0}/{1}").format(cdnurl or fmsurl, playpath),
                "pageUrl": self.url,
                "swfUrl": self.SWFURL,
                "live": True
            })
            streams["live"] = stream

        return streams

__plugin__ = UStreamTV
