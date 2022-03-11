"""
$description Live TV channels from TVR, a Romanian public, state-owned broadcaster.
$url tvrplus.ro
$type live
$region Romania
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tvrplus\.ro/live/"
))
class TVRPlus(Plugin):
    hls_file_re = re.compile(r"""["'](?P<url>[^"']+\.m3u8(?:[^"']+)?)["']""")

    stream_schema = validate.Schema(
        validate.all(
            validate.transform(hls_file_re.findall),
            validate.any(None, [validate.text])
        ),
    )

    def _get_streams(self):
        headers = {"Referer": self.url}
        stream_url = self.stream_schema.validate(self.session.http.get(self.url).text)
        if stream_url:
            stream_url = list(set(stream_url))
            for url in stream_url:
                log.debug("URL={0}".format(url))
                yield from HLSStream.parse_variant_playlist(self.session, url, headers=headers).items()


__plugin__ = TVRPlus
