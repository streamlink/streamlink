"""
$description Live TV channels and video on-demand service from ARD, a German public, independent broadcaster.
$url ardmediathek.de
$url mediathek.daserste.de
$type live, vod
$metadata id
$metadata author
$metadata title
$region Germany
"""

import re

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(\w+\.)?ardmediathek\.de/live(?:/(?:[^/]+/)?(?P<id_live>\w+))?(?:\?|$)"),
)
@pluginmatcher(
    name="video",
    pattern=re.compile(r"https?://(\w+\.)?ardmediathek\.de/video/(?:[^/]+/[^/]+/[^/]+/)?(?P<id_video>\w+)(?:\?|$)"),
)
class ARDMediathek(Plugin):
    _URL_API = "https://api.ardmediathek.de/page-gateway/pages/ard/item/{item}"
    _URL_NOW = "https://programm-api.ard.de/nownext/api/now"

    _SCHEMA_DATA = validate.Schema(
        validate.parse_json(),
        {
            "id": str,
            "widgets": validate.all(
                [dict],
                validate.filter(lambda item: item.get("mediaCollection")),
                validate.get(0),
                validate.none_or_all(
                    {
                        "geoblocked": bool,
                        "publicationService": {
                            "name": str,
                        },
                        "show": validate.none_or_all(
                            {"title": str},
                            validate.get("title"),
                        ),
                        "title": str,
                        "mediaCollection": {
                            "embedded": {
                                "streams": [
                                    validate.all(
                                        {
                                            "media": [
                                                {
                                                    "mimeType": str,
                                                    "url": validate.url(),
                                                    "maxVResolutionPx": int,
                                                },
                                            ],
                                        },
                                        validate.get("media"),
                                    ),
                                ],
                            },
                        },
                    },
                    validate.union_get(
                        "geoblocked",
                        ("mediaCollection", "embedded", "streams"),
                        ("publicationService", "name"),
                        "title",
                        "show",
                    ),
                ),
            ),
        },
    )

    def _get_streams(self):
        self.id = media_id = self.match["id_live"] if self.matches["live"] else self.match["id_video"]

        if self.matches["live"] and not media_id:
            media_id = self.session.http.get(
                self._URL_NOW,
                schema=validate.Schema(
                    validate.parse_json(),
                    {"channels": {str: dict}},
                    validate.get("channels"),
                    validate.transform(dict.keys),
                    validate.transform(list),
                    validate.get(0),
                ),
            )

        data = self.session.http.get(
            self._URL_API.format(item=media_id),
            params={
                "devicetype": "pc",
                "embedded": "false",
            },
            schema=self._SCHEMA_DATA,
        )
        if not data:
            return

        if not data["widgets"]:
            log.info("The content is unavailable")
            return

        geoblocked, streams, self.author, self.title, show = data["widgets"]
        if geoblocked:
            log.info("The content is not available in your region")
            return

        if show:
            show = show.strip()
            if not self.title:
                self.title = show
            elif show != self.title:
                self.title = f"{show}: {self.title}"

        result = []
        for stream in streams:
            for media in stream:
                match media["mimeType"]:
                    case "application/vnd.apple.mpegurl":
                        return HLSStream.parse_variant_playlist(self.session, media["url"])
                    case "video/mp4":
                        result.append((f"{media['maxVResolutionPx']}p", HTTPStream(self.session, media["url"])))
        return result


__plugin__ = ARDMediathek
