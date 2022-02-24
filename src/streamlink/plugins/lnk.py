import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?lnk\.lt/tiesiogiai(?:#(?P<channel>[a-z0-9]+))?"
))
class LNK(Plugin):
    API_URL = "https://lnk.lt/api/video/video-config/{0}"

    CHANNEL_MAP = {
        "lnk": 137535,
        "btv": 137534,
        "2tv": 95343,
        "infotv": 137748,
        "tv1": 106791
    }

    def _get_streams(self):
        match = self.match.groupdict()
        channel = match["channel"] or "lnk"
        try:
            channel_id = self.CHANNEL_MAP[channel]
        except KeyError:
            log.error("Unknown channel: {0}", channel)

        data = self.session.http.get(self.API_URL.format(channel_id)).json()
        hls_url = data["videoInfo"]["videoUrl"]
        yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = LNK
