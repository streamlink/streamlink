"""
$description Live TV channels and VODs from TVP, a Polish public, state-owned broadcaster.
$url stream.tvp.pl
$type live, vod
$notes Some VODs may be geo-restricted. Authentication is not supported.
"""

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        https?://
        (?:
            (?:tvpstream\.vod|stream)\.tvp\.pl(?:/(?:\?channel_id=(?P<channel_id>\d+))?)?$
            |
            vod\.tvp\.pl/[^/]+/.+,(?P<vod_id>\d+)$
        )
    """,
    re.VERBOSE,
))
class TVP(Plugin):
    _URL_PLAYER = "https://stream.tvp.pl/sess/TVPlayer2/embed.php"
    _URL_VOD = "https://vod.tvp.pl/api/products/{vod_id}/videos/playlist"

    def _get_video_id(self, channel_id: Optional[str]):
        items: List[Tuple[int, int]] = self.session.http.get(
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
                    [
                        validate.all(
                            {
                                "id": int,
                                "items": validate.none_or_all(
                                    [{
                                        "video_id": int,
                                    }],
                                    validate.get((0, "video_id")),
                                ),
                            },
                            validate.union_get("id", "items"),
                        ),
                    ],
                ),
            ),
        )

        if channel_id is not None:
            _channel_id = int(channel_id)
            try:
                return next(item[1] for item in items if item[0] == _channel_id)
            except StopIteration:
                pass

        return items[0][1] if items else None

    def _get_live(self, channel_id: Optional[str]):
        video_id = self._get_video_id(channel_id)
        if not video_id:
            log.error("Could not find video ID")
            return

        log.debug(f"video ID: {video_id}")

        streams: Optional[List[Tuple[str, str]]] = self.session.http.get(
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
                    "result": validate.none_or_all(
                        {
                            "content": {
                                "files": [
                                    validate.all(
                                        {
                                            "type": str,
                                            "url": validate.url(),
                                        },
                                        validate.union_get("type", "url"),
                                    ),
                                ],
                            },
                        },
                        validate.get(("content", "files")),
                    ),
                },
                validate.get("result"),
            ),
        )
        if not streams:
            return

        def get(items, condition):
            return next((_url for _stype, _url in items if condition(_stype, urlparse(_url).path)), None)

        # prioritize HLSStream and get the first available stream
        url = get(streams, lambda t, _: t == "hls")
        if url:
            return HLSStream.parse_variant_playlist(self.session, url)

        # fall back to DASHStream
        url = get(streams, lambda t, p: t == "any_native" and p.endswith(".mpd"))
        if url:
            return DASHStream.parse_manifest(self.session, url)

        # fall back to HTTPStream
        url = get(streams, lambda t, p: t == "any_native" and p.endswith(".mp4"))
        if url:
            return {"vod": HTTPStream(self.session, url)}

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
            return HLSStream.parse_variant_playlist(self.session, data["HLS"][0]["src"])

    def _get_streams(self):
        if self.match["vod_id"]:
            return self._get_vod(self.match["vod_id"])
        else:
            return self._get_live(self.match["channel_id"])


__plugin__ = TVP
