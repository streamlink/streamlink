"""
$description Live TV channels and video on-demand service from the SBA, a Saudi, state-owned broadcaster.
$url aloula.sba.sa
$url aloula.sa
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:aloula\.sba\.sa|(?:www\.)?aloula\.sa)/(?:\w{2}/)?live/(?P<live_slug>[^/?&]+)"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:aloula\.sba\.sa|(?:www\.)?aloula\.sa)/(?:\w{2}/)?episode/(?P<vod_id>\d+)"),
)
class Aloula(Plugin):
    _URL_API_CHANNELS = "https://aloula.faulio.com/api/v1/channels"
    _URL_API_CHANNELS_PLAYER = "https://aloula.faulio.com/api/v1.1/channels/{channel}/player"
    _URL_API_VIDEO = "https://aloula.faulio.com/api/v1/video/{vod_id}"
    _URL_API_VIDEO_PLAYER = "https://aloula.faulio.com/api/v1/video/{vod_id}/player"

    def get_live(self, live_slug):
        live_data = self.session.http.get(
            self._URL_API_CHANNELS,
            schema=validate.Schema(
                validate.parse_json(),
                [
                    {
                        "id": int,
                        "url": str,
                        "title": str,
                        "has_live": bool,
                        "has_vod": bool,
                    },
                ],
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

        hls_url = self.session.http.get(
            self._URL_API_CHANNELS_PLAYER.format(channel=self.id),
            schema=validate.Schema(
                validate.parse_json(),
                {"streams": {"hls": validate.url()}},
                validate.get(("streams", "hls")),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def get_vod(self, vod_id):
        vod_data = self.session.http.get(
            self._URL_API_VIDEO.format(vod_id=vod_id),
            acceptable_status=(200, 401),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "blocks": [
                                {
                                    "id": str,
                                    "program_title": str,
                                    "title": str,
                                    "season_number": int,
                                    "episode": int,
                                },
                            ],
                        },
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
            self._URL_API_VIDEO_PLAYER.format(vod_id=vod_id),
            schema=validate.Schema(
                validate.parse_json(),
                {"settings": {"protocols": {"hls": validate.url()}}},
                validate.get(("settings", "protocols", "hls")),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        self.session.http.headers.update({
            "Origin": "https://www.aloula.sa",
            "Referer": "https://www.aloula.sa/",
        })

        if self.matches["live"]:
            return self.get_live(self.match["live_slug"])
        else:
            return self.get_vod(self.match["vod_id"])


__plugin__ = Aloula
