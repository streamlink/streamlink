"""
$description TikTok is a short-form video hosting service owned by ByteDance.
$url www.tiktok.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import logging
import re
import sys

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/?]+)(?:$|/live)"),
)
@pluginmatcher(
    name="video",
    pattern=re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/?]+)/video/(?P<id>\d+)"),
)
class TikTok(Plugin):
    QUALITY_WEIGHTS: dict[str, int] = {}

    _URL_API_LIVE = "https://www.tiktok.com/api-live/user/room"

    _STATUS_OFFLINE = 4

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, key

        return super().stream_weight(key)

    def _query_api(self, url, **kwargs):
        schema = kwargs.pop("schema")

        success, data = self.session.http.get(
            url,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "statusCode": 0,
                            "data": schema,
                        },
                        validate.transform(lambda data: (True, data["data"])),
                    ),
                    validate.all(
                        {
                            "message": str,
                        },
                        validate.transform(lambda data: (False, data["message"])),
                    ),
                ),
            ),
            **kwargs,
        )

        if not success:
            log.error(data or "Error while querying API")
            return None

        return data

    def _get_streams_live(self):
        self.author = self.match["channel"]

        data = self._query_api(
            self._URL_API_LIVE,
            params={
                "aid": 1988,
                "sourceType": 54,
                "uniqueId": self.author,
            },
            headers={
                "Referer": self.url,
            },
            schema=validate.Schema(
                {
                    "liveRoom": {
                        "status": int,
                        validate.optional("streamId"): str,
                        "title": str,
                        validate.optional("streamData"): validate.all(
                            {
                                "pull_data": {
                                    "stream_data": validate.all(
                                        str,
                                        validate.parse_json(),
                                        {
                                            "data": dict,
                                        },
                                        validate.get("data"),
                                        {
                                            str: validate.all(
                                                {
                                                    "main": {
                                                        "flv": validate.url(),
                                                        "sdk_params": validate.all(
                                                            validate.parse_json(),
                                                            {
                                                                "vbitrate": int,
                                                            },
                                                        ),
                                                    },
                                                },
                                                validate.union_get(
                                                    ("main", "flv"),
                                                    ("main", "sdk_params", "vbitrate"),
                                                ),
                                            ),
                                        },
                                    ),
                                },
                            },
                            validate.get(("pull_data", "stream_data")),
                        ),
                    },
                },
                validate.get("liveRoom"),
                validate.union_get(
                    "status",
                    "streamId",
                    "title",
                    "streamData",
                ),
            ),
        )
        if not data:
            return

        status, self.id, self.title, stream_data = data
        if status == self._STATUS_OFFLINE:
            log.info("The channel is currently offline")
            return

        if not stream_data:
            log.error("The stream is inaccessible")
            return

        streams = {}
        for name, (url, vbitrate) in stream_data.items():
            self.QUALITY_WEIGHTS[name] = vbitrate
            streams[name] = HTTPStream(self.session, url)

        self.QUALITY_WEIGHTS["origin"] = sys.maxsize

        return streams

    def _get_streams_video(self):
        self.id = self.match["id"]

        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(
                    ".//script[@type='application/json'][@id='__UNIVERSAL_DATA_FOR_REHYDRATION__'][1]/text()",
                ),
                validate.none_or_all(
                    validate.parse_json(),
                    {
                        "__DEFAULT_SCOPE__": {
                            "webapp.video-detail": validate.any(
                                validate.all(
                                    {
                                        "statusCode": 0,
                                        "itemInfo": {
                                            "itemStruct": {
                                                "author": {
                                                    "uniqueId": str,
                                                },
                                                "video": {
                                                    "downloadAddr": validate.url(),
                                                },
                                            },
                                        },
                                    },
                                    validate.get(("itemInfo", "itemStruct")),
                                    validate.union_get(
                                        ("author", "uniqueId"),
                                        ("video", "downloadAddr"),
                                    ),
                                    validate.transform(lambda data: (True, data)),
                                ),
                                validate.all(
                                    {
                                        "statusMsg": str,
                                    },
                                    validate.transform(lambda data: (False, data["statusMsg"])),
                                ),
                            ),
                        },
                    },
                    validate.get(("__DEFAULT_SCOPE__", "webapp.video-detail")),
                ),
            ),
        )
        if not data:
            return
        if not data[0]:
            log.error(data[1] or "The video is inaccessible")
            return

        self.author, url = data[1]

        return {"video": HTTPStream(self.session, url)}

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_streams_live()
        elif self.matches["video"]:
            return self._get_streams_video()


__plugin__ = TikTok
