import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import parse_params
from streamlink.stream import HTTPStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"httpstream://(?P<url>\S+)(?:\s(?P<params>.+))?"
))
class HTTPStreamPlugin(Plugin):
    def _get_streams(self):
        data = self.match.groupdict()
        url = update_scheme("http://", data.get("url"))
        params = parse_params(data.get("params"))
        log.debug(f"URL={url}; params={params}")

        return {"live": HTTPStream(self.session, url, **params)}


__plugin__ = HTTPStreamPlugin
