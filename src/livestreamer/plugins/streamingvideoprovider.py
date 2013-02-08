from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HLSStream
from livestreamer.utils import urlget, res_xml, get_node_text

from time import time
import re

class Streamingvideoprovider(Plugin):
    SWFURL = "http://play.streamingvideoprovider.com/player2.swf"
    APIURL = "http://player.webvideocore.net/index.php"

    @classmethod
    def can_handle_url(self, url):
        return "streamingvideoprovider.co.uk" in url

    def _get_hls_streams(self, channelname):
        options = dict(l="info", a="ajax_video_info", file=channelname,
                       rid=time())
        res = urlget(self.APIURL, params=options)

        match = re.search("'(http://.+\.m3u8)'", res.text)
        if not match:
            raise PluginError(("No HLS playlist found on URL {0}").format(self.url))

        playlisturl = match.group(1)
        self.logger.debug("Playlist URL is {0}", playlisturl)
        playlist = {}
        playlist["hls"] = HLSStream(self.session, playlisturl)

        return playlist

    def _get_rtmp_streams(self, channelname):
        options = dict(l="info", a="xmlClipPath", clip_id=channelname,
                       rid=time())
        res = urlget(self.APIURL, params=options)

        dom = res_xml(res)
        rtmpurl = dom.getElementsByTagName("url")
        rtmp = None

        if len(rtmpurl) > 0:
            rtmp = get_node_text(rtmpurl[0])
        else:
            raise PluginError(("No RTMP Streams found on URL {0}").format(self.url))

        rtmplist = {}
        rtmplist["live"] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "swfVfy": self.SWFURL,
            "live": True
        })

        return rtmplist

    def _get_streams(self):
        channelname = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()
        streams = {}

        if RTMPStream.is_usable(self.session):
            try:
                rtmpstreams = self._get_rtmp_streams(channelname)
                streams.update(rtmpstreams)
            except PluginError as err:
                self.logger.error("Error when fetching RTMP stream info: {0}", str(err))
        else:
            self.logger.warning("rtmpdump is not usable, only HLS streams will be available")

        try:
            hlsstreams = self._get_hls_streams(channelname)
            streams.update(hlsstreams)
        except PluginError as err:
            self.logger.error("Error when fetching HLS stream info: {0}", str(err))

        return streams


__plugin__ = Streamingvideoprovider
