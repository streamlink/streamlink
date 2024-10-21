"""
$description Japanese live-streaming and video hosting platform owned by PIA Corporation.
$url ulizaportal.jp
$type live, vod
$metadata id
$metadata title
$account Purchased tickets are required.
$notes Tickets purchased at "PIA LIVE STREAM" are used for this platform.
"""

import logging
import re
import time
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https://ulizaportal\.jp/pages/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})"),
)
class PIAULIZAPortal(Plugin):
    _URL_PLAYER_DATA = "https://player-api.p.uliza.jp/v1/players/"
    _URL_PLAYLIST = "https://vms-api.p.uliza.jp/v1/prog-index.m3u8"

    def _get_streams(self):
        self.id = self.match.group("id")

        try:
            expires = int(dict(parse_qsl(urlparse(self.url).query)).get("expires", 0))
        except ValueError:
            expires = 0
        if 0 < expires <= time.time():
            log.error("The URL has expired")
            return None

        self.title, player_data_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.union((
                    validate.xml_xpath_string(".//head/title[1]/text()"),
                    validate.xml_xpath_string(
                        f".//script[@type='text/javascript'][contains(@src,'{self._URL_PLAYER_DATA}')][1]/@src",
                    ),
                )),
            ),
        )
        if not player_data_url:
            log.error("Player data URL not found")
            return None

        m3u8_url = self.session.http.get(
            player_data_url,
            headers={
                "Referer": self.url,
            },
            schema=validate.Schema(
                re.compile(rf"""{re.escape(self._URL_PLAYLIST)}[^"']+"""),
                validate.none_or_all(
                    validate.get(0),
                    validate.url(),
                ),
            ),
        )
        if not m3u8_url:
            log.error("Playlist URL not found")
            return None

        return HLSStream.parse_variant_playlist(self.session, m3u8_url)


__plugin__ = PIAULIZAPortal
