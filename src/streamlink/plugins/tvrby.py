"""
$description Live TV channels from BTRC, a Belarusian public, state-owned broadcaster.
$url tvr.by
$type live
$region Belarus
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tvr\.by/televidenie/belarus"
))
class TVRBy(Plugin):
    file_re = re.compile(r"""(?P<url>https://stream\.hoster\.by[^"',]+\.m3u8[^"',]*)""")
    player_re = re.compile(r"""["'](?P<url>[^"']+tvr\.by/plugines/online-tv-main\.php[^"']+)["']""")

    stream_schema = validate.Schema(
        validate.all(
            validate.transform(file_re.finditer),
            validate.transform(list),
            [validate.get("url")],
            # remove duplicates
            validate.transform(set),
            validate.transform(list),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ensure the URL ends with a /
        if not self.url.endswith("/"):
            self.url += "/"

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.player_re.search(res.text)
        if not m:
            return

        player_url = m.group("url")
        res = self.session.http.get(player_url)
        stream_urls = self.stream_schema.validate(res.text)
        log.debug("Found {0} stream URL{1}".format(len(stream_urls), "" if len(stream_urls) == 1 else "s"))

        for stream_url in stream_urls:
            yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()


__plugin__ = TVRBy
