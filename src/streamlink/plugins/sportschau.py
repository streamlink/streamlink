"""
$description German sports magazine live stream, owned by ARD.
$url sportschau.de
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:\w+\.)*sportschau\.de/",
    )
)
class Sportschau(Plugin):
    def _get_streams(self):
        streams = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string("(//*[@data-v-type='MediaPlayer'])[1]/@data-v"),
                validate.parse_json(),
                validate.get("mc"),
                validate.get("streams"),
            ),
        )
        for stream in streams:
            for media in stream.get("media"):
                url = media.get("url")
                is_hls = media.get("mimeType") == "application/vnd.apple.mpegurl"
                is_audio_only = stream.get("isAudioOnly")
                if is_hls:
                    yield from HLSStream.parse_variant_playlist(self.session, url).items()
                else:
                    media_type = "audio" if is_audio_only else "video"
                    yield media_type, HTTPStream(self.session, url)


__plugin__ = Sportschau
