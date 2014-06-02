"""Plugin for Viasat's on demand content sites, such as tv6play.se."""

import re

from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream, RTMPStream
from livestreamer.utils import rtmpparse

STREAM_API_URL = "http://playapi.mtgx.tv/v1/videos/stream/{0}"

_swf_url_re = re.compile("data-flashplayer-url=\"([^\"]+)\"")

_url_re = re.compile("""
    http(s)?://(www\.)?
    (?:
        tv(3|6|8|10)play |
        viasat4play
    )
    \.
    (?:
        dk|ee|lt|lv|no|se
    )
    /.+/
    (?P<stream_id>\d+)
""", re.VERBOSE)

_stream_schema = validate.Schema(
    {
        "streams": validate.all(
            { validate.text: validate.any(validate.text, int, None) },
            validate.filter(lambda k,v: isinstance(v, validate.text))
        )
    },
    validate.get("streams")
)


class Viasat(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_swf_url(self):
        res = http.get(self.url)
        match = _swf_url_re.search(res.text)
        if not match:
            raise PluginError("Unable to find SWF URL in the HTML")

        return match.group(1)

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        stream_id = match.group("stream_id")
        res = http.get(STREAM_API_URL.format(stream_id))
        stream_info = http.json(res, schema=_stream_schema)
        streams = {}
        swf_url = None
        for name, stream_url in stream_info.items():
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
