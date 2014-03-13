from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream, HLSStream

from time import time
import re


class Livestation(Plugin):
    SWFURL = "http://beta.cdn.livestation.com/player/5.10/livestation-player.swf"
    APIURL = "http://tokens.api.livestation.com/channels/{0}/tokens.json?{1}"

    @classmethod
    def can_handle_url(self, url):
        return "livestation.com" in url

    def _get_rtmp_streams(self, text):
        match = re.search("streamer=(rtmp://.+?)&", text)
        if not match:
            raise PluginError(("No RTMP streamer found on URL {0}").format(self.url))

        rtmp = match.group(1)

        match = re.search("<meta content=\"(http://.+?\.swf)\?", text)
        if not match:
            self.logger.warning("Failed to get player SWF URL location on URL {0}", self.url)
        else:
            self.SWFURL = match.group(1)
            self.logger.debug("Found player SWF URL location {0}", self.SWFURL)

        match = re.search("<meta content=\"(.+)\" name=\"item-id\" />", text)
        if not match:
            raise PluginError(("Missing channel item-id on URL {0}").format(self.url))

        res = http.get(self.APIURL.format(match.group(1), time()), params=dict(output="json"))
        json = http.json(res)

        if not isinstance(json, list):
            raise PluginError("Invalid JSON response")

        rtmplist = {}

        for jdata in json:
            if "stream_name" not in jdata or "type" not in jdata:
                continue

            if "rtmp" not in jdata["type"]:
                continue

            playpath = jdata["stream_name"]

            if "token" in jdata and jdata["token"]:
                playpath += jdata["token"]

            if len(json) == 1:
                stream_name = "live"
            else:
                stream_name = jdata["stream_name"]

            rtmplist[stream_name] = RTMPStream(self.session, {
                "rtmp": rtmp,
                "pageUrl": self.url,
                "swfVfy": self.SWFURL,
                "playpath": playpath,
                "live": True
            })

        return rtmplist

    def _get_hls_streams(self, text):
        match = re.search("\"(http://.+\.m3u8)\"", text)
        if not match:
            raise PluginError(("No HLS playlist found on URL {0}").format(self.url))

        playlisturl = match.group(1)
        self.logger.debug("Playlist URL is {0}", playlisturl)
        playlist = {}

        try:
            playlist = HLSStream.parse_variant_playlist(self.session, playlisturl)
        except IOError as err:
            raise PluginError(err)

        return playlist

    def _get_streams(self):
        res = http.get(self.url)
        streams = {}

        if RTMPStream.is_usable(self.session):
            try:
                rtmpstreams = self._get_rtmp_streams(res.text)
                streams.update(rtmpstreams)
            except PluginError as err:
                self.logger.error("Error when fetching RTMP stream info: {0}", str(err))
        else:
            self.logger.warning("rtmpdump is not usable, only HLS streams will be available")

        try:
            hlsstreams = self._get_hls_streams(res.text)
            streams.update(hlsstreams)
        except PluginError as err:
            self.logger.error("Error when fetching HLS stream info: {0}", str(err))

        return streams


__plugin__ = Livestation

