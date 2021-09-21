import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import parse_params
from streamlink.stream.akamaihd import AkamaiHDStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"akamaihd://(?P<url>\S+)(?:\s(?P<params>.+))?"
))
class AkamaiHDPlugin(Plugin):
    def _get_streams(self):
        data = self.match.groupdict()
        url = update_scheme("http://", data.get("url"))
        params = parse_params(data.get("params"))
        log.debug("URL={0}; params={1}".format(url, params))

        return {"live": AkamaiHDStream(self.session, url, **params)}


__plugin__ = AkamaiHDPlugin
