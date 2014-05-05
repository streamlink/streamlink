"""Plugin for Viasat's on demand content sites, such as tv6play.se."""

import re

from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream, RTMPStream
from livestreamer.utils import rtmpparse, verifyjson

STREAM_API = "http://playapi.mtgx.tv/v1/videos/stream/{0}"
SWF_URL_REGEX = r"data-flashplayer-url=\"([^\"]+)\""
URL_REGEX = (r"http(s)?://(www\.)?"
             r"(tv(3|6|8|10)|viasat4)play\.(dk|ee|lt|lv|no|se)"
             r"/.+/(?P<stream_id>\d+)")


class Viasat(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return re.match(URL_REGEX, url)

    def _get_swf_url(self):
        res = http.get(self.url)
        match = re.search(SWF_URL_REGEX, res.text)
        if not match:
            raise PluginError("Unable to find SWF URL in the HTML")

        return match.group(1)

    def _get_streams(self):
        match = re.match(URL_REGEX, self.url)
        if not match:
            return

        stream_id = match.group("stream_id")
        res = http.get(STREAM_API.format(stream_id))
        json = http.json(res)
        stream_info = verifyjson(json, "streams")

        streams = {}
        swf_url = None
        for name, stream_url in stream_info.items():
            stream_url = str(stream_url)
            if stream_url.endswith(".m3u8"):
                try:
                    hls_streams = HLSStream.parse_variant_playlist(self.session,
                                                                   stream_url)
                    streams.update(hls_streams)
                except IOError as err:
                    self.logger.error("Failed to fetch HLS streams: {0}", err)
            elif stream_url.startswith("rtmp://"):
                swf_url = swf_url or self._get_swf_url()
                params = {
                    "rtmp": stream_url,
                    "pageUrl": self.url,
                    "swfVfy": swf_url,
                }

                if stream_url.endswith(".mp4"):
                    tcurl, playpath = rtmpparse(stream_url)
                    params["rtmp"] = tcurl
                    params["playpath"] = playpath
                else:
                    params["live"] = True

                streams[name] = RTMPStream(self.session, params)

        return streams

__plugin__ = Viasat
