"""
$description Live TV channel and video on-demand service from TV5Monde, a French free-to-air broadcaster.
$url tv5monde.com
$url tivi5mondeplus.com
$type live, vod
$region France, Belgium, Switzerland, Africa
"""

import re
from urllib.parse import quote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


@pluginmatcher(
    re.compile(r"https?://(?:[\w-]+\.)*(?:tv5monde|tivi5mondeplus)\.com/"),
)
class TV5Monde(Plugin):
    _URL_API = "https://api.tv5monde.com/player/asset/{asset}/resolve"

    _MAP_STREAMTYPES = {
        "application/x-mpegURL": HLSStream.parse_variant_playlist,
        "application/dash+xml": DASHStream.parse_manifest,
        "video/mp4": lambda *args: {"vod": HTTPStream(*args)},
    }

    def _find_streams(self, data):
        schema_streams = validate.Schema([
            validate.all(
                {
                    "type": str,
                    "url": validate.url(),
                },
                validate.union_get("type", "url"),
            ),
        ])
        streams = schema_streams.validate(data)

        for mimetype, streamfactory in self._MAP_STREAMTYPES.items():
            for streamtype, streamurl in streams:
                if streamtype == mimetype:
                    url = update_scheme("https://", streamurl)
                    return streamfactory(self.session, url)

    def _get_playlist(self, data):
        schema_playlist = validate.Schema(
            validate.parse_json(),
            [{"sources": list}],
            validate.get((0, "sources")),
        )
        playlist = schema_playlist.validate(data)

        return self._find_streams(playlist)

    def _get_broadcast(self, data):
        schema_broadcast = validate.Schema(
            validate.parse_json(),
            [
                {
                    "type": str,
                    "url": str,
                },
            ],
        )
        broadcast = schema_broadcast.validate(data)

        deferred = next((item["url"] for item in broadcast if item["type"] == "application/deferred"), None)
        if deferred:
            url = self._URL_API.format(asset=quote(deferred))
            broadcast = self.session.http.get(
                url,
                schema=validate.Schema(
                    validate.parse_json(),
                ),
            )

        return self._find_streams(broadcast)

    def _get_streams(self):
        playlist, broadcast = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.union((
                    validate.xml_xpath_string(".//*[@data-playlist][1]/@data-playlist"),
                    validate.xml_xpath_string(".//*[@data-broadcast][1]/@data-broadcast"),
                )),
            ),
        )

        # data-playlist needs higher priority (data-broadcast attribute exists on the same DOM node)
        if playlist:
            return self._get_playlist(playlist)
        if broadcast:
            return self._get_broadcast(broadcast)


__plugin__ = TV5Monde
