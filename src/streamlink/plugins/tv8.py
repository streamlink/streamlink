import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://www\.tv8\.com\.tr/canli-yayin'
))
class TV8(Plugin):
    _re_hls = re.compile(r"""file\s*:\s*(["'])(?P<hls_url>https?://.*?\.m3u8.*?)\1""")

    title = "TV8"

    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(self._re_hls.search),
            validate.any(None, validate.get("hls_url"))
        ))
        if hls_url is not None:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TV8
