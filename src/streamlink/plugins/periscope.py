import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)

STREAM_INFO_URL = "https://api.periscope.tv/api/v2/getAccessPublic"

STATUS_GONE = 410
STATUS_UNAVAILABLE = (STATUS_GONE,)

_url_re = re.compile(r"http(s)?://(www\.)?(periscope|pscp)\.tv/[^/]+/(?P<broadcast_id>[\w\-\=]+)")
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
        res = self.session.http.get(
            STREAM_INFO_URL,
            params=match.groupdict(),
            acceptable_status=STATUS_UNAVAILABLE
        )

        if res.status_code in STATUS_UNAVAILABLE:
            return

        data = self.session.http.json(res, schema=_stream_schema)
        if data.get("hls_url"):
            hls_url = data["hls_url"]
            hls_name = "live"
        elif data.get("replay_url"):
            log.info("Live Stream ended, using replay instead")
            hls_url = data["replay_url"]
            hls_name = "replay"
        else:
            raise NoStreamsError(self.url)

        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not streams:
            return {hls_name: HLSStream(self.session, hls_url)}
        else:
            return streams


__plugin__ = Periscope
