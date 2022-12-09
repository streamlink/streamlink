"""
$description Japanese live-streaming service used primarily by Japanese idols & voice actors and their fans.
$url showroom-live.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?showroom-live\.com/"
))
class Showroom(Plugin):
    LIVE_STATUS = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.set_option("hls-playlist-reload-time", "segment")

    def _get_streams(self):
        room_id = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'share_url:\"https:')][1]/text()"),
                validate.none_or_all(
                    re.compile(r"share_url:\"https:[^?]+?\?room_id=(?P<room_id>\d+)\""),
                    validate.any(None, validate.get("room_id")),
                ),
            ),
        )
        if not room_id:
            return

        live_status, self.title = self.session.http.get(
            "https://www.showroom-live.com/api/live/live_info",
            params={
                "room_id": room_id,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "live_status": int,
                    "room_name": str,
                },
                validate.union_get(
                    "live_status",
                    "room_name",
                ),
            ),
        )
        if live_status != self.LIVE_STATUS:
            log.info("This stream is currently offline")
            return

        url = self.session.http.get(
            "https://www.showroom-live.com/api/live/streaming_url",
            params={
                "room_id": room_id,
                "abr_available": 1,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {"streaming_url_list": [{
                    "type": str,
                    "url": validate.url(),
                }]},
                validate.get("streaming_url_list"),
                validate.filter(lambda p: p["type"] == "hls_all"),
                validate.get((0, "url")),
            ),
        )

        res = self.session.http.get(url, acceptable_status=(200, 403, 404))
        if res.headers["Content-Type"] != "application/x-mpegURL":
            log.error("This stream is restricted")
            return

        return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = Showroom
