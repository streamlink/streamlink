"""Plugin for Arte.tv, bi-lingual art and culture channel."""

import re

from itertools import chain

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream, HTTPStream, RTMPStream

SWF_URL = "http://www.arte.tv/player/v2/jwplayer6/mediaplayer.6.6.swf"

_url_re = re.compile("http(s)?://(\w+\.)?arte.tv/")
_json_re = re.compile("arte_vp_(?:live-)?url=\"([^\"]+)\"")

_schema = validate.Schema(
    validate.transform(_json_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.url(scheme="http")
        )
    )
)
_video_schema = validate.Schema({
    "videoJsonPlayer": {
        "VSR": validate.any(
            [],
            {
                validate.text: {
                    "height": int,
                    "mediaType": validate.text,
                    "url": validate.text,
                    validate.optional("streamer"): validate.text
                },
            },
        ),
        "VTY": validate.text
    }
})


class ArteTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _create_stream(self, stream, is_live):
        stream_name = "{0}p".format(stream["height"])
        stream_type = stream["mediaType"]
        stream_url = stream["url"]

        if stream_type in ("hls", "mp4"):
            if urlparse(stream_url).path.endswith("m3u8"):
                try:
                    streams = HLSStream.parse_variant_playlist(self.session, stream_url)

                    # TODO: Replace with "yield from" when dropping Python 2.
                    for stream in streams.items():
                        yield stream
                except IOError as err:
                    self.logger.error("Failed to extract HLS streams: {0}", err)
            else:
                yield stream_name, HTTPStream(self.session, stream_url)

        elif stream_type == "rtmp":
            params = {
                "rtmp": stream["streamer"],
                "playpath": stream["url"],
                "swfVfy": SWF_URL,
                "pageUrl": self.url,
            }

            if is_live:
                params["live"] = True
            else:
                params["playpath"] = "mp4:{0}".format(params["playpath"])

            stream = RTMPStream(self.session, params)
            yield stream_name, stream

    def _get_streams(self):
        json_url = http.get(self.url, schema=_schema)
        if not json_url:
            return

        res = http.get(json_url)
        video = http.json(res, schema=_video_schema)

        if not video["videoJsonPlayer"]["VSR"]:
            return

        is_live = video["videoJsonPlayer"]["VTY"] == "LIVE"
        vsr = video["videoJsonPlayer"]["VSR"].values()
        streams = (self._create_stream(stream, is_live) for stream in vsr)

        return chain.from_iterable(streams)

__plugin__ = ArteTV
