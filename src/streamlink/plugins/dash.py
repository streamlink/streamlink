import re
from urllib.parse import urlparse

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import LOW_PRIORITY, parse_params, stream_weight
from streamlink.stream.dash import DASHStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"dash://(?P<url>\S+)(?:\s(?P<params>.+))?$"),
)
@pluginmatcher(
    priority=LOW_PRIORITY,
    pattern=re.compile(
        # URL with explicit scheme, or URL with implicit HTTPS scheme and a path
        r"(?P<url>[^/]+/\S+\.mpd(?:\?\S*)?)(?:\s(?P<params>.+))?$",
        re.IGNORECASE,
    ),
)
class MPEGDASH(Plugin):
    @classmethod
    def stream_weight(cls, stream: str) -> tuple[float, str]:
        match = re.match(r"^(?:(.*)\+)?(?:a(\d+)k)$", stream)
        if match and match.group(1) and match.group(2):
            weight, group = stream_weight(match.group(1))
            weight += int(match.group(2))
            return weight, group
        elif match and match.group(2):
            return stream_weight(f"{match.group(2)}k")
        else:
            return stream_weight(stream)

    def _get_streams(self):
        data = self.match.groupdict()
        url = update_scheme("https://", data.get("url", ""), force=False)
        params = parse_params(data.get("params"))
        log.debug("URL=%s; params=%r", url, params)

        parsed = urlparse(url)
        if parsed.scheme != "file" and not parsed.netloc:
            log.error("Input URL is missing a host or input file path is missing the file:// scheme")
            return

        return DASHStream.parse_manifest(self.session, url, **params)


__plugin__ = MPEGDASH
