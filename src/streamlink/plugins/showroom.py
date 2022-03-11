"""
$description Japanese live streaming service used primarily by Japanese idols & voice actors and their fans.
$url showroom-live.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker

log = logging.getLogger(__name__)


class ShowroomHLSStreamWorker(HLSStreamWorker):
    def _playlist_reload_time(self, playlist, sequences):
        return 1.5


class ShowroomHLSStreamReader(HLSStreamReader):
    __worker__ = ShowroomHLSStreamWorker


class ShowroomHLSStream(HLSStream):
    __reader__ = ShowroomHLSStreamReader


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?showroom-live\.com/"
))
class Showroom(Plugin):
    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[@id='js-live-data'][@data-json]/@data-json"),
                validate.any(None, validate.all(
                    validate.parse_json(),
                    {"is_live": int,
                     "room_id": int,
                     validate.optional("room"): {"content_region_permission": int, "is_free": int}},
                ))
            )
        )
        if not data:  # URL without livestream
            return

        log.debug(f"{data!r}")
        if data["is_live"] != 1:
            log.info("This stream is currently offline")
            return

        url = self.session.http.get(
            "https://www.showroom-live.com/api/live/streaming_url",
            params={"room_id": data["room_id"], "abr_available": 1},
            schema=validate.Schema(
                validate.parse_json(),
                {"streaming_url_list": [{
                    "type": str,
                    "url": validate.url(),
                }]},
                validate.get("streaming_url_list"),
                validate.filter(lambda p: p["type"] == "hls_all"),
                validate.get((0, "url"))
            ),
        )
        res = self.session.http.get(url, acceptable_status=(200, 403, 404))
        if res.headers["Content-Type"] != "application/x-mpegURL":
            log.error("This stream is restricted")
            return
        return ShowroomHLSStream.parse_variant_playlist(self.session, url)


__plugin__ = Showroom
