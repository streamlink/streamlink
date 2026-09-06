"""
$description Live TV channels and video on-demand service from ZDF, a German public, independent broadcaster.
$url zdf.de
$type live, vod
$metadata id
$metadata title
$region Germany
"""

from __future__ import annotations

import re

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:\w+\.)?zdf\.de/play/(?P<category>[^/]+)/[^/]+/(?P<video_id>[^\s?#]+)"),
)
class ZDFMediathek(Plugin):
    _URL_CONFIGURATION = "https://ngp.zdf.de/configs/zdf/zdfmt25/configuration.json"
    _URL_API = "https://api.zdf.de/{path}"

    # noinspection GraphQLUnresolvedReference
    # language=graphql
    _QUERY_VIDEO_BY_CANONICAL = """
        query VideoByCanonical($canonical: String!) {
            videoByCanonical(canonical: $canonical) {
                id
                title
                currentMedia {
                    nodes {
                        ptmdTemplate
                        ... on LiveMedia {
                            liveMediaType
                        }
                        ... on VodMedia {
                            vodMediaType
                        }
                    }
                }
            }
        }
    """

    def _video_by_canonical(self, auth: str, canonical: str):
        return self.session.http.post(
            self._URL_API.format(path="graphql"),
            headers={
                "Api-Auth": f"Bearer {auth}",
            },
            json={
                "operationName": "VideoByCanonical",
                "query": re.sub(r"\s+", " ", self._QUERY_VIDEO_BY_CANONICAL).strip(),
                "variables": {
                    "canonical": canonical,
                },
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "videoByCanonical": validate.none_or_all(
                            {
                                "id": str,
                                "title": str,
                                "currentMedia": validate.all(
                                    {
                                        "nodes": [
                                            validate.all(
                                                {
                                                    "ptmdTemplate": str,
                                                    validate.optional("liveMediaType"): str,
                                                    validate.optional("vodMediaType"): str,
                                                },
                                                validate.union_get(
                                                    "ptmdTemplate",
                                                    "liveMediaType",
                                                    "vodMediaType",
                                                ),
                                            ),
                                        ],
                                    },
                                    validate.get("nodes"),
                                ),
                            },
                            validate.union_get(
                                "id",
                                "title",
                                "currentMedia",
                            ),
                        ),
                    },
                },
                validate.get(("data", "videoByCanonical")),
            ),
        )

    def _get_stream_data(self, auth: str, path: str):
        return self.session.http.get(
            self._URL_API.format(path=path.lstrip("/")),
            headers={
                "Api-Auth": f"Bearer {auth}",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "priorityList": [
                        validate.all(
                            {
                                "formitaeten": [
                                    validate.all(
                                        {
                                            "mimeType": str,
                                            "qualities": [
                                                validate.all(
                                                    {
                                                        "quality": str,
                                                        validate.optional("highestVerticalResolution"): int,
                                                        "audio": {
                                                            "tracks": [
                                                                validate.all(
                                                                    {
                                                                        "class": str,
                                                                        "uri": validate.url(),
                                                                    },
                                                                    validate.union_get(
                                                                        "class",
                                                                        "uri",
                                                                    ),
                                                                ),
                                                            ],
                                                        },
                                                    },
                                                    validate.union_get(
                                                        "quality",
                                                        "highestVerticalResolution",
                                                        ("audio", "tracks"),
                                                    ),
                                                ),
                                            ],
                                        },
                                        validate.union_get(
                                            "mimeType",
                                            "qualities",
                                        ),
                                    ),
                                ],
                            },
                            validate.get("formitaeten", []),
                        ),
                    ],
                },
                validate.get(("priorityList", 0), []),
            ),
        )

    def _get_api_token(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'apiAuthToken')][1]/text()"),
                validate.none_or_all(
                    validate.regex(re.compile(r"""self\.__next_f\.push\(\[\d+,\s*(?P<data>".+?")]\)""")),
                    validate.get("data"),
                    validate.parse_json(),
                    validate.regex(re.compile(r'''"apiAuthToken":"(?P<token>.+?)"''')),
                    validate.get("token"),
                ),
            ),
        )

    def _get_player_id(self):
        return self.session.http.get(
            self._URL_CONFIGURATION,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "ptmdPlayerId": str,
                },
                validate.get("ptmdPlayerId"),
            ),
        )

    def _get_streams(self) -> dict | None:
        if self.match["category"] == "zapping":
            log.error("Zapping video URLs are not supported")
            return None

        player_id = self._get_player_id()
        api_token = self._get_api_token()

        data = self._video_by_canonical(auth=api_token, canonical=self.match["video_id"])
        if not data:
            return None

        media: list[tuple[str, str | None, str | None]]
        self.id, self.title, media = data

        path: str | None = next(
            (path for path, *media_types in media if "DEFAULT" in media_types),
            next((path for path, *_ in media), None),
        )
        if not path:
            return None

        stream_data = self._get_stream_data(auth=api_token, path=path.replace("{playerId}", player_id, 1))

        result = {}
        for stream_type, qualities in stream_data:
            for quality, resolution, streams in qualities:
                for stream_class, url in streams:
                    if stream_class != "main":
                        continue
                    match stream_type:
                        case "application/x-mpegURL" if quality == "auto":
                            return HLSStream.parse_variant_playlist(self.session, url)
                        case _ if stream_type.startswith("video/"):
                            result[f"{resolution}p"] = HTTPStream(self.session, url)

        return result


__plugin__ = ZDFMediathek
