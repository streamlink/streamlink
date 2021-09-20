import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?latina\.pe/tvenvivo"
))
class Latina(Plugin):
    title = "Latina"

    def _get_streams(self):
        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
            "Referer": self.url})

        self.session.http.get(self.url)
        stream_url = None
        for div in itertags(self.session.http.get(self.url).text, "div"):
            if div.attributes.get("id") == "player":
                stream_url = div.attributes.get("data-stream")

        if stream_url:
            log.debug("URL={0}".format(stream_url))
            return HLSStream.parse_variant_playlist(self.session,
                                                    stream_url,
                                                    name_fmt="{pixels}_{bitrate}")


__plugin__ = Latina
