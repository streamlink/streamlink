"""
$description A state/privately owned Russian live TV channel.
$url 1tv.ru
$type live
$region Russia
"""

import logging
import random
import re
from urllib.parse import unquote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?1tv\.ru/live",
))
@pluginmatcher(re.compile(
    r"https?://static\.1tv\.ru/eump/(?:embeds|pages)/1tv_live(?:_orbit-plus-4)?\.html",
))
class OneTV(Plugin):
    def _get_streams(self):
        if "orbit-plus-4" in self.url:
            channel = "1tv-orbit-plus-4"
            self.title = "Первый канал HD (+4)"
        else:
            channel = "1tvch"
            self.title = "Первый канал HD"

        url = self.session.http.get(
            f"https://stream.1tv.ru/api/playlist/{channel}_as_array.json",
            data={"r": random.randint(1, 100000)},
            schema=validate.Schema(
                validate.parse_json(),
                {"hls": [validate.url()]},
                validate.get(("hls", 0)),
            ))

        if not url:
            return

        log.debug(f"{url}")
        if "georestrictions" in url:
            log.error("Stream is geo-restricted")
            return

        hls_session = self.session.http.get(
            "https://stream.1tv.ru/get_hls_session",
            schema=validate.Schema(
                validate.parse_json(),
                {"s": validate.transform(unquote)},
            ))
        url = update_qsd(url, qsd=hls_session, safe="/:")

        return HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}")


__plugin__ = OneTV
