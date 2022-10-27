"""
$description Live TV channels and VODs from TVP, a Polish public, state-owned broadcaster.
$url stream.tvp.pl
$type live, vod
$notes Some VODs may be geo-restricted. Authentication is not supported.
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        https?://
        (?:
            (?:tvpstream\.vod|stream)\.tvp\.pl(?:/(?:\?channel_id=(?P<video_id>\d+))?)?$
            |
            vod\.tvp\.pl/[^/]+/.+,(?P<vod_id>\d+)$
        )
    """,
    re.VERBOSE,
))
class TVP(Plugin):
    _URL_PLAYER = "https://stream.tvp.pl/sess/TVPlayer2/embed.php"
    _URL_VOD = "https://vod.tvp.pl/api/products/{vod_id}/videos/playlist"

    def _get_video_id(self):
        return self.session.http.get(
            self.url,
            headers={
                # required, otherwise the next request for retrieving the HLS URL will be aborted by the server
                "Connection": "close",
            },
            schema=validate.Schema(
                re.compile(r"window\.__channels\s*=\s*(?P<json>\[.+?])\s*;", re.DOTALL),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    [{
                        "items": validate.none_or_all(
                            [{
                                "video_id": int,
                            }],
                        ),
                    }],
                    validate.get((0, "items", 0, "video_id")),
                ),
            ),
        )

    def _get_live(self, video_id):
        video_id = video_id or self._get_video_id()
        if not video_id:
            log.error("Could not find video ID")
            return

        log.debug(f"video ID: {video_id}")

        return self.session.http.get(
            self._URL_PLAYER,
            params={
                "ID": video_id,
                "autoPlay": "without_audio",
            },
            headers={
                "Referer": self.url,
            },
            schema=validate.Schema(
                re.compile(r"window\.__api__\s*=\s*(?P<json>\{.+?})\s*;", re.DOTALL),
                validate.get("json"),
                validate.parse_json(),
                {
                    "result": {
                        "content": {
                            "files": validate.all(
                                [{
                                    "type": str,
                                    "url": validate.url(),
                                }],
                                validate.filter(lambda item: item["type"] == "hls"),
                            ),
                        },
                    },
                },
                validate.get(("result", "content", "files", 0, "url")),
            ),
        )

    def _get_vod(self, vod_id):
        data = self.session.http.get(
            self._URL_VOD.format(vod_id=vod_id),
            params={
                "platform": "BROWSER",
                "videoType": "MOVIE",
            },
            acceptable_status=(200, 403),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"code": "GEOIP_FILTER_FAILED"},
                    validate.all(
                        {
                            "sources": {
                                validate.optional("HLS"): [{
                                    "src": validate.url(),
                                }],
                            },
                        },
                        validate.get("sources"),
                    ),
                ),
            ),
        )

        if data.get("code") == "GEOIP_FILTER_FAILED":
            log.error("The content is not available in your region")
            return

        if data.get("HLS"):
            return data["HLS"][0]["src"]

    def _get_streams(self):
        if self.match["vod_id"]:
            hls_url = self._get_vod(self.match["vod_id"])
        else:
            hls_url = self._get_live(self.match["video_id"])

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TVP
