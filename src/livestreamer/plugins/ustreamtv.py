from livestreamer.compat import str, urlparse
from livestreamer.packages.flashmedia import AMFPacket, AMFError
from livestreamer.plugin import Plugin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.stream import HLSStream, RTMPStream
from livestreamer.utils import urlget

from io import BytesIO

import re

class UStreamTV(Plugin):
    AMFURL = "http://cgw.ustream.tv/Viewer/getStream/1/{0}.amf"
    SWFURL = "http://static-cdn1.ustream.tv/swf/live/viewer3:50.swf"

    @classmethod
    def can_handle_url(self, url):
        return "ustream.tv" in url

    def _get_channel_id(self, url):
        match = re.search("ustream.tv/embed/(\d+)", url)
        if match:
            return int(match.group(1))

        res = urlget(url)

        match = re.search("\"cid\":(\d+)", res.text)
        if match:
            return int(match.group(1))

    def _create_stream(self, cdn, streamname):
        parsed = urlparse(cdn)
        options = dict(rtmp=cdn, app=parsed.path[1:],
                       playpath=streamname, pageUrl=self.url,
                       swfUrl=self.SWFURL, live=True)
        return RTMPStream(self.session, options)

    def _get_streams(self):
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)


        self.logger.debug("Fetching stream info")
        res = urlget(self.AMFURL.format(channelid))

        try:
            packet = AMFPacket.deserialize(BytesIO(res.content))
        except (IOError, AMFError) as err:
            raise PluginError(("Failed to parse AMF packet: {0}").format(str(err)))

        result = None
        for message in packet.messages:
            if message.target_uri == "/1/onResult":
                result = message.value
                break

        if not result:
            raise PluginError("No result found in AMF packet")

        streams = {}

        if "liveHttpUrl" in result:
            try:
                hlsstreams = HLSStream.parse_variant_playlist(self.session,
                                                              result["liveHttpUrl"])
                streams.update(hlsstreams)
            except IOError as err:
                self.logger.warning("Failed to get variant playlist: {0}", err)

        if "streamName" in result:
            if "cdnUrl" in result:
                cdn = result["cdnUrl"]
            elif "fmsUrl" in result:
                cdn = result["fmsUrl"]
            else:
                self.logger.warning("Missing cdnUrl and fmsUrl from result")
                return streams

            if "videoCodec" in result and result["videoCodec"]["height"] > 0:
                streamname = "{0}p".format(int(result["videoCodec"]["height"]))
            else:
                streamname = "live"

            streams[streamname] = self._create_stream(cdn, result["streamName"])

        if "streamVersions" in result:
            for version, info in result["streamVersions"].items():
                if "streamVersionCdn" in info:
                    for name, cdn in info["streamVersionCdn"].items():
                        if "cdnStreamUrl" in cdn and "cdnStreamName" in cdn:
                            cdnname = "live_alt_{0}".format(name)
                            streams[cdnname] = self._create_stream(cdn["cdnStreamUrl"],
                                                                   cdn["cdnStreamName"])



        return streams

__plugin__ = UStreamTV
