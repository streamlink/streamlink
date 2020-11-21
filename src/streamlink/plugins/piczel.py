import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


STREAMS_URL = "https://piczel.tv/api/streams?followedStreams=false&live_only=false&sfw=false"
HLS_URL = "https://piczel.tv/hls/{0}/index.m3u8"

_url_re = re.compile(r"https://piczel.tv/watch/(\w+)")

_streams_schema = validate.Schema([
    {
        "id": int,
        "live": bool,
        "slug": validate.text
    }
])


class Piczel(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        channel_name = match.group(1)

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
