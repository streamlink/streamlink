"""
$description Japanese live-streaming and video hosting platform owned by PIA Corporation.
$url ulizaportal.jp
$type live, vod
$account Purchased tickets are required.
$notes Tickets purchased at "PIA LIVE STREAM" are used for this platform.
"""

import re
import time

from streamlink.exceptions import FatalPluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(
        r"https://ulizaportal\.jp/pages/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})(\?expires=(?P<expires>\d+).*)?",
    ),
)
class PIAULIZAPortal(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.headers.update({"Referer": "https://ulizaportal.jp/"})

    def _get_streams(self):
        self.id = self.match.group("id")

        expires = self.match.group("expires")
        if expires and int(expires) <= time.time():
            raise FatalPluginError("The link is expired")

        self.title, player_data_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.union(
                    (
                        validate.xml_xpath_string(".//head/title[1]/text()"),
                        validate.xml_xpath_string(
                            ".//script[@type='text/javascript'][contains(@src,'https://player-api.p.uliza.jp/v1/players/')]/@src",
                        ),
                    ),
                ),
            ),
        )

        m3u8_url = self.session.http.get(
            player_data_url,
            schema=validate.Schema(
                re.compile(r"""https://vms-api.p.uliza.jp/v1/prog-index.m3u8[^"]+"""),
                validate.get(0),
                validate.url(),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, m3u8_url)


__plugin__ = PIAULIZAPortal
