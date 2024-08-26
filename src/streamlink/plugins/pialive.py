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
from urllib.parse import urlencode

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://player\.pia-live\.jp/stream/(?P<video_key>[\w-]+)",
))
class PiaLive(Plugin):
    _URL_BASE = "https://player.pia-live.jp/"
    _URL_API = "https://api.pia-live.jp/"
    _ULIZA_URL_PLAYER_DATA = "https://player-api.p.uliza.jp/v1/players/"
    _ULIZA_URL_PLAYLIST = "https://vms-api.p.uliza.jp/v1/prog-index.m3u8"

    def _extract_vars_validate_pattern(self, xml_xpath, variable):
        return validate.all(
            validate.xml_xpath_string(xml_xpath),
            str,
            validate.regex(re.compile(rf'(?:var|const)\s+{variable}\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1')),
            validate.get("value"),
        )

    def _get_streams(self):
        self.video_key = self.match.group("video_key")
        self.title, programCode, prod_configure_path = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.union((
                    validate.xml_xpath_string(".//head/title[1]/text()"),
                    self._extract_vars_validate_pattern(".//script[contains(text(),'programCode')][1]/text()", "programCode"),
                    validate.xml_xpath_string(".//script[@type='text/javascript'][contains(@src,'/statics/js/s_prod')][1]/@src"),
            )),
        ))
        apiKey = self.session.http.get(
            self._URL_BASE + prod_configure_path,
            schema=validate.Schema(
                validate.parse_html(),
                self._extract_vars_validate_pattern("", "APIKEY"),
            ),
            headers={"Referer": self._URL_BASE},
        )

        player_script_tag = self.session.http.post(
            f"{self._URL_API}/perf/player-tag-list/{programCode}",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": self._URL_BASE},
            data=urlencode({"play_url": self.video_key, "api_key": apiKey}),
            schema=validate.Schema(
                validate.parse_json(),
            ),
        )["data"]["movie_one_tag"]
        player_url = validate.Schema(
                validate.regex(re.compile(r'\s+src=(["\'])(?P<player_url>.*?)\1')),
            ).validate(player_script_tag)["player_url"]

        if not player_url:
            log.error("Player URL not found")
            return None

        return self.handle_embed_player(player_url)

    def handle_embed_player(self, player_url):
        m3u8_url = None
        if player_url.startswith(self._ULIZA_URL_PLAYER_DATA):
            m3u8_url = self.session.http.get(
                player_url,
                headers={
                    "Referer": self._URL_BASE,
                },
                schema=validate.Schema(
                    re.compile(rf"""{re.escape(self._ULIZA_URL_PLAYLIST)}[^"']+"""),
                    validate.none_or_all(
                        validate.get(0),
                        validate.url(),
                    ),
                ),
            )
        if not m3u8_url:
            log.error("Platform not supported yet.")
            return None

        return HLSStream.parse_variant_playlist(self.session, m3u8_url)


__plugin__ = PiaLive
