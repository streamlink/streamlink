import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import LOW_PRIORITY, parse_params
from streamlink.stream import HDSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"hds://(?P<url>\S+)(?:\s(?P<params>.+))?"
))
@pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
    r"(?P<url>\S+\.f4m(?:\?\S*)?)(?:\s(?P<params>.+))?"
))
class HDSPlugin(Plugin):
    def _get_streams(self):
        data = self.match.groupdict()
        url = update_scheme("http://", data.get("url"))
        params = parse_params(data.get("params"))
        log.debug(f"URL={url}; params={params}")

        return HDSStream.parse_manifest(self.session, url, **params)


__plugin__ = HDSPlugin
