"""
$description Live TV channels and video on-demand service from the SBA, a Saudi, state-owned broadcaster.
$url aloula.sa
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?aloula\.sa/(?:\w{2}/)?
    (?:
        live/(?P<live_slug>[^/?&]+)
    |
        episode/(?P<vod_id>\d+)
    )
""", re.VERBOSE))
class Aloula(Plugin):
    def get_live(self, live_slug):
        live_data = self.session.http.get(
            "https://aloula.faulio.com/api/v1/channels",
            schema=validate.Schema(
                validate.parse_json(),
                [{
                    "id": int,
                    "url": str,
                    "title": str,
                    "has_live": bool,
                    "has_vod": bool,
                    "streams": {
                        "hls": validate.url(),
                    },
                }],
                validate.filter(lambda k: k["url"] == live_slug),
            ),
        )
        if not live_data:
            return
        live_data = live_data[0]
        log.trace(f"{live_data!r}")

        if not live_data["has_live"]:
            log.error("Stream is not live")
            return

        self.id = live_data["id"]
        self.author = "SBA"
        self.title = live_data["title"]
        self.category = "Live"
        return HLSStream.parse_variant_playlist(self.session, live_data["streams"]["hls"])

    def get_vod(self, vod_id):
        vod_data = self.session.http.get(
            f"https://aloula.faulio.com/api/v1/video/{vod_id}",
            acceptable_status=(200, 401),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"blocks": [{
                            "id": str,
                            "program_title": str,
                            "title": str,
                            "season_number": int,
                            "episode": int,
                        }]},
                        validate.get(("blocks", 0)),
                    ),
                    {"cms_error": str, "message": str},
                ),
            ),
        )

        log.trace(f"{vod_data!r}")
        if "cms_error" in vod_data and vod_data["cms_error"] == "auth":
            log.error("This stream requires a login; specify appropriate Authorization and profile HTTP headers")
            return
        if "cms_error" in vod_data:
            log.error(f"API error: {vod_data['cms_error']} ({vod_data['message']})")
            return
        self.id = vod_data["id"]
        self.author = vod_data["program_title"]
        self.title = vod_data["title"]
        self.category = f"S{vod_data['season_number']}E{vod_data['episode']}"

        hls_url = self.session.http.get(
            f"https://aloula.faulio.com/api/v1/video/{vod_id}/player",
            schema=validate.Schema(
                validate.parse_json(),
                {"settings": {"protocols": {"hls": validate.url()}}},
                validate.get(("settings", "protocols", "hls")),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        live_slug = self.match.group("live_slug")
        vod_id = self.match.group("vod_id")

        if live_slug:
            return self.get_live(live_slug)
        elif vod_id:
            return self.get_vod(vod_id)


__plugin__ = Aloula
