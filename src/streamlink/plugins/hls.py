import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import LOW_PRIORITY, parse_params
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"hls(?:variant)?://(?P<url>\S+)(?:\s(?P<params>.+))?$"),
)
@pluginmatcher(
    priority=LOW_PRIORITY,
    pattern=re.compile(
        # URL with explicit scheme, or URL with implicit HTTPS scheme and a path
        r"(?P<url>[^/]+/\S+\.m3u8(?:\?\S*)?)(?:\s(?P<params>.+))?$",
        re.IGNORECASE,
    ),
)
class HLSPlugin(Plugin):
    def _get_streams(self):
        data = self.match.groupdict()
        url = update_scheme("https://", data.get("url"), force=False)
        params = parse_params(data.get("params"))
        log.debug(f"URL={url}; params={params}")

        streams = HLSStream.parse_variant_playlist(self.session, url, **params)

        return streams or {"live": HLSStream(self.session, url, **params)}


__plugin__ = HLSPlugin
