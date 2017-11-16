"""Plugin for Arte.tv, bi-lingual art and culture channel."""

import re

from itertools import chain

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream

JSON_VOD_URL = "https://api.arte.tv/api/player/v1/config/{0}/{1}?platform=ARTE_NEXT"
JSON_LIVE_URL = "https://api.arte.tv/api/player/v1/livestream/{0}"

_url_re = re.compile(r"""
    https?://(?:\w+\.)?arte\.tv/(?:guide/)?
    (?P<language>[a-z]{2})/
    (?:
        (?:videos/)?(?P<video_id>(?!RC\-|videos)[^/]+?)/.+ | # VOD
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
                    "versionShortLibelle": validate.text
                },
            },
        )
    }
})


class ArteTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _create_stream(self, stream, language):
        stream_name = "{0}p".format(stream["height"])
        stream_type = stream["mediaType"]
        stream_url = stream["url"]
        stream_language = stream["versionShortLibelle"]

        if language == "de":
            language = ["DE", "VOST-DE", "VA", "VOA", "Dt. Live", "OV", "OmU"]
        elif language == "en":
            language = ["ANG", "VOST-ANG"]
        elif language == "es":
            language = ["ESP", "VOST-ESP"]
        elif language == "fr":
            language = ["FR", "VOST-FR", "VF", "VOF", "Frz. Live", "VO", "ST mal"]
        elif language == "pl":
            language = ["POL", "VOST-POL"]

        if stream_language in language:
            if stream_type in ("hls", "mp4"):
                if urlparse(stream_url).path.endswith("m3u8"):
                    try:
                        streams = HLSStream.parse_variant_playlist(self.session, stream_url)

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

        vsr = video["videoJsonPlayer"]["VSR"].values()
        streams = (self._create_stream(stream, language) for stream in vsr)

        return chain.from_iterable(streams)


__plugin__ = ArteTV
