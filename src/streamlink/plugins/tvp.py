"""
$description Live TV channels and VODs from TVP, a Polish public, state-owned broadcaster.
$url vod.tvp.pl
$url tvp.info
$url sport.tvp.pl
$type live, vod
$metadata id
$metadata title
$region Poland
$notes Some live streams and VODs may be geo-restricted. Authentication is not supported.
"""

from __future__ import annotations

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://vod\.tvp\.pl/live,\d+/[^,]+,(?P<channel_id>\d+)(?:/.+,(?P<show_id>\d+)$)?",
    ),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(
        r"https?://vod\.tvp\.pl/(?!live,)[^/]+/.+,(?P<vod_id>\d+)$",
    ),
)
@pluginmatcher(
    name="tvp_info",
    pattern=re.compile(
        r"https?://(?:www\.)?tvp\.info/",
    ),
)
@pluginmatcher(
    name="tvp_sport",
    pattern=re.compile(
        r"https?://sport\.tvp\.pl/(?P<stream_id>\d+)/.+",
    ),
)
class TVP(Plugin):
    _URL_VOD = "https://vod.tvp.pl/api/products/{vod_id}/videos/playlist"
    _URL_INFO_API_TOKEN = "https://api.tvp.pl/tokenizer/token/{token}"
    _URL_INFO_API_NEWS = "https://www.tvp.info/api/info/news?device=www&id={id}"
    _URL_INFO_API_BLOCK = "https://www.tvp.info/api/info/block?device=www&id={id}"
    _URL_INFO_API_BLOCK_LIST = "https://www.tvp.info/api/info/block/list?device=www&id={id}"

    def _get_formats_from_api(self, token):
        is_geo_blocked, self.title, formats = self.session.http.get(
            self._URL_INFO_API_TOKEN.format(token=token),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status": "OK",
                    "isGeoBlocked": bool,
                    "title": str,
                    "formats": [
                        validate.all(
                            {
                                "mimeType": str,
                                "url": validate.url(),
                            },
                            validate.union_get("mimeType", "url"),
                        ),
                    ],
                },
                validate.union_get("isGeoBlocked", "title", "formats"),
            ),
        )
        if is_geo_blocked:
            log.error("The content is not available in your region")
            raise NoStreamsError

        for mime_type, url in formats:
            if mime_type == "application/x-mpegurl":
                yield from HLSStream.parse_variant_playlist(self.session, url).items()
            if mime_type == "application/dash+xml":
                yield from DASHStream.parse_manifest(self.session, url).items()

    def _get_vod(self, vod_id: str, video_type: str = "MOVIE"):
        data = self.session.http.get(
            self._URL_VOD.format(vod_id=vod_id),
            params={
                "platform": "BROWSER",
                "videoType": video_type,
            },
            acceptable_status=(200, 403),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"code": str},
                    validate.all(
                        {
                            "sources": {
                                validate.optional("HLS"): [
                                    {
                                        "src": validate.url(),
                                    },
                                ],
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

        if data.get("code") == "ITEM_NOT_PAID":
            log.error("The content is not accessible")
            return

        if data.get("HLS"):
            return HLSStream.parse_variant_playlist(self.session, data["HLS"][0]["src"])

    def _get_tvp_info(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'window.__pageSettings')][1]/text()"),
                validate.none_or_all(
                    str,
                    validate.regex(re.compile(r"window\.__pageSettings\s*=\s*(?P<json>{.*?})\s*;", re.DOTALL)),
                    validate.get("json"),
                    validate.parse_json(),
                    {
                        "type": str,
                        "id": int,
                    },
                    validate.union_get("type", "id"),
                ),
            ),
        )
        if not data:
            return

        vod_type, self.id = data
        if vod_type == "NEWS":
            self.id, self.title = self.session.http.get(
                self._URL_INFO_API_NEWS.format(id=self.id),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "data": {
                            "video": {
                                "title": str,
                                "_id": int,
                            },
                        },
                    },
                    validate.get(("data", "video")),
                    validate.union_get("_id", "title"),
                ),
            )
        elif vod_type == "SG":
            self.id = self.session.http.get(
                self._URL_INFO_API_BLOCK_LIST.format(id=self.id),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "data": {
                            "items": validate.all(
                                [
                                    {
                                        "_id": int,
                                        "type": str,
                                    },
                                ],
                                validate.filter(lambda obj: obj["type"] == "LIVE"),
                                validate.get(0),
                                validate.none_or_all(validate.get("_id")),
                            ),
                        },
                    },
                    validate.get(("data", "items")),
                ),
            )
            if not self.id:
                return
            self.id = self.session.http.get(
                self._URL_INFO_API_BLOCK.format(id=self.id),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "data": {
                            "live_items": validate.all(
                                [
                                    {
                                        "_id": int,
                                        "type": str,
                                    },
                                ],
                                validate.filter(lambda obj: obj["type"] == "VIDEO"),
                                validate.get(0),
                                validate.none_or_all(validate.get("_id")),
                            ),
                        },
                    },
                    validate.get(("data", "live_items")),
                ),
            )
            if not self.id:
                return

        yield from self._get_formats_from_api(self.id)

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_vod(self.match["channel_id"], "LIVE")
        if self.matches["vod"]:
            return self._get_vod(self.match["vod_id"], "MOVIE")
        if self.matches["tvp_info"]:
            return self._get_tvp_info()
        if self.matches["tvp_sport"]:
            return self._get_formats_from_api(self.match["stream_id"])

        return None


__plugin__ = TVP
