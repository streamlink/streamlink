import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import LOW_PRIORITY, stream_weight
from streamlink.stream.dash import DASHStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"dash://(?P<url>.+)"
))
@pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
    r"(?P<url>.+\.mpd(?:\?.*)?)"
))
class MPEGDASH(Plugin):
    @classmethod
    def stream_weight(cls, stream):
        match = re.match(r"^(?:(.*)\+)?(?:a(\d+)k)$", stream)
        if match and match.group(1) and match.group(2):
            weight, group = stream_weight(match.group(1))
            weight += int(match.group(2))
            return weight, group
        elif match and match.group(2):
            return stream_weight(match.group(2) + 'k')
        else:
            return stream_weight(stream)

    def _get_streams(self):
        url = self.match.group(1)
        log.debug(f"Parsing MPD URL: {url}")

        return DASHStream.parse_manifest(self.session, url)


__plugin__ = MPEGDASH
