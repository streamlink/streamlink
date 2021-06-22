import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import parse_params
from streamlink.stream import RTMPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"(?P<url>rtmp(?:e|s|t|te)?://\S+)(?:\s(?P<params>.+))?"
))
class RTMPPlugin(Plugin):
    def _get_streams(self):
        data = self.match.groupdict()
        params = parse_params(data.get("params"))
        params["rtmp"] = data.get("url")

        for boolkey in ("live", "realtime", "quiet", "verbose", "debug"):
            if boolkey in params:
                params[boolkey] = bool(params[boolkey])

        log.debug(f"params={params}")

        return {"live": RTMPStream(self.session, params)}


__plugin__ = RTMPPlugin
