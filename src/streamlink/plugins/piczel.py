"""
$description Global live streaming platform for the creative community.
$url piczel.tv
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


STREAMS_URL = "https://piczel.tv/api/streams?followedStreams=false&live_only=false&sfw=false"
HLS_URL = "https://piczel.tv/hls/{0}/index.m3u8"

_streams_schema = validate.Schema([
    {
        "id": int,
        "live": bool,
        "slug": validate.text
    }
])


@pluginmatcher(re.compile(
    r"https?://piczel\.tv/watch/(\w+)"
))
class Piczel(Plugin):
    def _get_streams(self):
        channel_name = self.match.group(1)

        res = self.session.http.get(STREAMS_URL)
        streams = self.session.http.json(res, schema=_streams_schema)

        for stream in streams:
            if stream["slug"] != channel_name:
                continue

            if not stream["live"]:
                return

            log.debug(f"HLS stream URL: {HLS_URL.format(stream['id'])}")

            return {"live": HLSStream(self.session, HLS_URL.format(stream["id"]))}


__plugin__ = Piczel
