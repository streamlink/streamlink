import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import RTMPStream

log = logging.getLogger(__name__)


class RTMPPlugin(Plugin):
    _url_re = re.compile(r"rtmp(?:e|s|t|te)?://.+")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        params["rtmp"] = url

        for boolkey in ("live", "realtime", "quiet", "verbose", "debug"):
            if boolkey in params:
                params[boolkey] = bool(params[boolkey])

        log.debug("params={0}".format(params))
        return {"live": RTMPStream(self.session, params)}


__plugin__ = RTMPPlugin
