"""
$description Live TV and video on-demand service owned by Paramount Streaming.
$url pluto.tv
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import json
import re
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import parse_qsl, urljoin, urlparse
from uuid import uuid4

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSSegment, HLSStream, HLSStreamReader, HLSStreamWriter, M3U8Parser
from streamlink.utils.url import update_qsd


log = getLogger(__name__)


@dataclass(kw_only=True)
class PlutoHLSSegment(HLSSegment):
    ad: bool = False

    _RE_AD: ClassVar[re.Pattern[str]] = re.compile(
        r"""
            _ad(?:/|%2F|_bumper)
            |
            plutotv_filler
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __post_init__(self):
        self.ad = self._is_ad()

    def _is_ad(self) -> bool:
        parsed = urlparse(self.uri)

        if parsed.hostname and parsed.hostname.endswith("dai.google.com"):
            return True

        return re.search(self._RE_AD, parsed.path or "") is not None


class PlutoM3U8Parser(M3U8Parser):
    __segment__ = PlutoHLSSegment


class PlutoHLSStreamWriter(HLSStreamWriter):
    def should_filter_segment(self, segment: PlutoHLSSegment):  # type: ignore[override, ty:invalid-method-override]
        return segment.ad or super().should_filter_segment(segment)


class PlutoHLSStreamReader(HLSStreamReader):
    __writer__ = PlutoHLSStreamWriter


class PlutoHLSStream(HLSStream):
    __shortname__ = "hls-pluto"
    __reader__ = PlutoHLSStreamReader
    __parser__ = PlutoM3U8Parser


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2,}/)?(?:\w{2,}/)?live-tv/#?(?P<id>[^/?]+)",
    ),
)
@pluginmatcher(
    name="series",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2,}/)?(?:on-demand/series|shows)/(?P<id_s>[^/]+)(?:/season/\d+)?/episode/#?(?P<id_e>[^/?]+)",
    ),
)
@pluginmatcher(
    name="movies",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2,}/)?(?:on-demand/movies|movies)/#?(?P<id>[^/?]+)",
    ),
)
class Pluto(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        self._app_version = None
        if not (m := re.search(r"Firefox/(\d+(?:\.\d+)*)", useragents.FIREFOX)):
            raise PluginError("Could not find Firefox version")
        self._device_version = m[1]
        self._client_id = str(uuid4())

    @property
    def app_version(self):
        if self._app_version:
            return self._app_version

        self._app_version = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.any(
                    validate.all(
                        validate.xml_xpath_string(".//head/meta[(@name='appVersion' or @name='app_version')][1]/@content"),
                        str,
                    ),
                    validate.all(
                        validate.xml_xpath_string(".//script[@id='__NEXT_DATA__'][1]/text()"),
                        validate.none_or_all(
                            validate.parse_json(),
                            {"props": {"globalAppVersion": str}},
                            validate.get(("props", "globalAppVersion")),
                        ),
                    ),
                ),
                validate.any(None, str),
            ),
        )
        if not self._app_version:
            raise PluginError("Could not find pluto app version")

        log.debug("self._app_version: %s", self._app_version)

        return self._app_version

    def _graphql_request(self, url: str, operation_name: str, extensions: dict, variables: dict, schema):
        return self.session.http.get(
            url,
            params={
                "extensions": json.dumps(extensions, separators=(",", ":")),
                "variables": json.dumps(variables, separators=(",", ":")),
                "operationName": operation_name,
            },
            headers={"apollo-require-preflight": "true"},
            schema=schema,
        )

    def _get_series_metadata(self) -> dict:
        data = self._graphql_request(
            "https://pluto.tv/api/tn/hubs/graphql/",
            "FullEpisodesData",
            {"tnPersistedDocumentHash": "c33226b006b70748f919b5a1ea58d4f07c28cce943d1d2cc0a86fe10fd761b27"},
            {
                "showId": self.match["id_s"],
                "apiRawContentId": None,
                "withApiRaw": False,
                "episodeId": self.match["id_e"],
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "fullEpisodes": validate.none_or_all(
                            {
                                "episodes": [
                                    {
                                        "contentId": str,
                                        validate.optional("seriesTitle"): str,
                                        validate.optional("genre"): str,
                                        validate.optional("title"): str,
                                    },
                                ],
                            },
                            validate.get("episodes"),
                            validate.filter(lambda x: x.get("contentId") == self.match["id_e"]),
                            validate.get(0),
                        ),
                    },
                },
                validate.get(("data", "fullEpisodes")),
            ),
        )
        log.debug("_get_series_metadata: %s", data)
        return data or {}

    def _resolve_channel_origin_id(self, origin_id):
        return self._graphql_request(
            "https://pluto.tv/api/tn/video/graphql/",
            "ChannelsOne",
            {"tnPersistedDocumentHash": "b9c2b93c341345b0c990fa85bd9b596944c7f343d11ed066d2e1e2db42b1f7ca"},
            {
                "params": {
                    "userRegistrationCountry": "US",
                    "userState": "ANONYMOUS",
                    "packageCode": "NEW_FREE_PACKAGE",
                    "userProfileType": "ADULT",
                    "billingVendor": "cbscomp",
                    "dma": 0,
                    "stationId": None,
                    "channelCategorySlug": None,
                    "platformType": "Desktop",
                    "showListing": True,
                    "hideChannelsWithoutListings": True,
                    "rows": 20,
                    "numOfUpcomingListings": 0,
                    "filterLockedChannels": False,
                    "isPreviewMode": False,
                    "channelOriginId": int(origin_id),
                },
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "channels": {
                            validate.optional("channel"): validate.none_or_all(
                                {
                                    "videoContentId": str,
                                    "channelName": str,
                                },
                                validate.get("videoContentId"),
                            ),
                        },
                    },
                },
                validate.get(("data", "channels", "channel")),
            ),
        )

    def _get_api_data(self, request):
        log.debug("_get_api_data: %s", request)

        schema_paths = validate.any(
            validate.all(
                {
                    "paths": [
                        validate.all(
                            {
                                "type": str,
                                "path": str,
                            },
                            validate.union_get("type", "path"),
                        ),
                    ],
                },
                validate.get("paths"),
            ),
            validate.all(
                {
                    "path": str,
                },
                validate.transform(lambda obj: [("hls", obj["path"])]),
            ),
        )
        schema_live = [
            {
                "name": str,
                "id": str,
                "slug": str,
                "stitched": schema_paths,
            },
        ]
        schema_vod = [
            {
                "name": str,
                "id": str,
                "slug": str,
                "genre": str,
                "stitched": validate.any(schema_paths, {}),
                validate.optional("seasons"): [
                    {
                        "episodes": [
                            {
                                "name": str,
                                "_id": str,
                                "slug": str,
                                "stitched": schema_paths,
                            },
                        ],
                    },
                ],
            },
        ]

        return self.session.http.get(
            "https://boot.pluto.tv/v4/start",
            params={
                "appName": "web",
                "appVersion": self.app_version,
                "deviceVersion": self._device_version,
                "deviceModel": "web",
                "deviceMake": "firefox",
                "deviceType": "web",
                "clientID": self._client_id,
                "clientModelNumber": "1.0.0",
                "serverSideAds": "false",
                **request,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "servers": {
                        "stitcher": validate.url(),
                    },
                    "stitcherParams": str,
                    "sessionToken": str,
                    validate.optional("EPG"): schema_live,
                    validate.optional("VOD"): schema_vod,
                },
            ),
        )

    def _get_streams_live(self):
        origin_id = self.match["id"]

        if not origin_id.isdigit():
            video_content_id = origin_id
        elif not (video_content_id := self._resolve_channel_origin_id(origin_id)):
            return

        data = self._get_api_data({"channelSlug": video_content_id})
        epg = data.get("EPG", [])
        media = next((e for e in epg if e["id"] == video_content_id), None)
        if not media:
            return

        self.id = media["id"]
        self.title = media["name"]

        return data, media["stitched"]

    def _get_streams_series(self):
        episode_id = self.match["id_e"]
        data = self._get_api_data({})
        stitched_path = f"/stitch/hls/episode/{episode_id}/master.m3u8"

        metadata = self._get_series_metadata()
        self.id = episode_id
        self.author = metadata.get("seriesTitle")
        self.category = metadata.get("genre")
        self.title = metadata.get("title")

        return data, [("hls", stitched_path)]

    def _get_streams_movies(self):
        data = self._get_api_data({"seriesIDs": self.match["id"]})
        vod = data.get("VOD", [])
        media = next((v for v in vod if v["id"] == self.match["id"]), None)
        if not media:
            return

        self.id = media["id"]
        self.category = media["genre"]
        self.title = media["name"]

        return data, media["stitched"]

    def _get_streams(self):
        res = None
        if self.matches["live"]:
            res = self._get_streams_live()
        elif self.matches["series"]:
            res = self._get_streams_series()
        elif self.matches["movies"]:
            res = self._get_streams_movies()

        if not res:
            return

        data, paths = res
        for mediatype, path in paths:
            if mediatype != "hls":
                continue

            params = dict(parse_qsl(data["stitcherParams"]))
            params["jwt"] = data["sessionToken"]
            params["includeExtendedEvents"] = "true"
            params["masterJWTPassthrough"] = "true"
            url = urljoin(data["servers"]["stitcher"], "v2" + path)
            url = update_qsd(url, params)

            return PlutoHLSStream.parse_variant_playlist(self.session, url)


__plugin__ = Pluto
