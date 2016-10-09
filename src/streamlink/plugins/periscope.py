import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream


STREAM_INFO_URL = "https://api.periscope.tv/api/v2/getAccessPublic"

STATUS_GONE = 410
STATUS_UNAVAILABLE = (STATUS_GONE,)

_url_re = re.compile(r"http(s)?://(www\.)?periscope.tv/[^/]+/(?P<broadcast_id>[\w\-\=]+)")
_stream_schema = validate.Schema(
    validate.any(
        None,
        validate.union({
            "hls_url": validate.all(
                {"hls_url": validate.url(scheme="http")},
                validate.get("hls_url")
            ),
        }),
        validate.union({
            "replay_url": validate.all(
                {"replay_url": validate.url(scheme="http")},
                validate.get("replay_url")
            ),
        }),
    ),
)


class Periscope(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        res = http.get(STREAM_INFO_URL,
                       params=match.groupdict(),
                       acceptable_status=STATUS_UNAVAILABLE)

        if res.status_code in STATUS_UNAVAILABLE:
            return

        playlist_url = http.json(res, schema=_stream_schema)
        if "hls_url" in playlist_url:
            return dict(replay=HLSStream(self.session, playlist_url["hls_url"]))
        elif "replay_url" in playlist_url:
            self.logger.info("Live Stream ended, using replay instead")
            return dict(replay=HLSStream(self.session, playlist_url["replay_url"]))
        else:
            return

__plugin__ = Periscope
