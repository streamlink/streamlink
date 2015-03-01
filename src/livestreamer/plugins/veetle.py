import re

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import FLVPlaylist, HTTPStream

API_URL = "http://veetle.com/index.php/stream/ajaxStreamLocation/{0}/flash"

_url_re = re.compile("""
    http(s)?://(\w+\.)?veetle.com
    (:?
        /.*(v|view)/
        (?P<channel>[^/]+/[^/&?]+)
    )?
""", re.VERBOSE)

_schema = validate.Schema({
    validate.optional("isLive"): bool,
    "payload": validate.any(int, validate.url(scheme="http")),
    "success": bool
})


class Veetle(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        self.url = http.resolve_url(self.url)
        match = _url_re.match(self.url)
        parsed = urlparse(self.url)
        if parsed.fragment:
            channel_id = parsed.fragment
        elif parsed.path[:3] == '/v/':
            channel_id = parsed.path.split('/')[-1]
        else:
            channel_id = match.group("channel")

        if not channel_id:
            return

        channel_id = channel_id.lower().replace("/", "_")
        res = http.get(API_URL.format(channel_id))
        info = http.json(res, schema=_schema)

        if not info["success"]:
            return

        if info.get("isLive"):
            name = "live"
        else:
            name = "vod"

        stream = HTTPStream(self.session, info["payload"])
        # Wrap the stream in a FLVPlaylist to verify the FLV tags
        stream = FLVPlaylist(self.session, [stream])

        return {name: stream}

__plugin__ = Veetle
