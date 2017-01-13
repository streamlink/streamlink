"""Plugin for Arte.tv, bi-lingual art and culture channel."""

import re

from itertools import chain

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream, RTMPStream

SWF_URL = "http://www.arte.tv/player/v2/jwplayer6/mediaplayer.6.6.swf"
JSON_VOD_URL = "https://api.arte.tv/api/player/v1/config/{}/{}"
JSON_LIVE_URL = "https://api.arte.tv/api/player/v1/livestream/{}"

_url_re = re.compile(r"""
    https?://(?:\w+\.)?arte.tv/guide/
    (?P<language>[a-z]{2})/
    (?:
        (?P<video_id>.+?)/.+ | # VOD
        (?:direct|live)        # Live TV
    )
""", re.VERBOSE)

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

        elif stream_type == "f4m":
            try:
                streams = HDSStream.parse_manifest(self.session, stream_url)

                for stream in streams.items():
                    yield stream
            except IOError as err:
                self.logger.error("Failed to extract HDS streams: {0}", err)

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
        match = _url_re.match(self.url)
        language = match.group('language')
        video_id = match.group('video_id')
        if video_id is None:
            json_url = JSON_LIVE_URL.format(language)
        else:
            json_url = JSON_VOD_URL.format(language, video_id)
        res = http.get(json_url)
        video = http.json(res, schema=_video_schema)

        if not video["videoJsonPlayer"]["VSR"]:
            return

        is_live = video["videoJsonPlayer"]["VTY"] == "LIVE"
        vsr = video["videoJsonPlayer"]["VSR"].values()
        streams = (self._create_stream(stream, is_live) for stream in vsr)

        return chain.from_iterable(streams)


__plugin__ = ArteTV
