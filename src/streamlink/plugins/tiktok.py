"""
$description TikTok is a short-form video hosting service owned by ByteDance.
$url www.tiktok.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream


if TYPE_CHECKING:
    from collections.abc import Iterator

    from streamlink.stream.stream import Stream


log = getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/?]+)(?:$|/live)"),
)
@pluginmatcher(
    name="video",
    pattern=re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/?]+)/video/(?P<id>\d+)"),
)
class TikTok(Plugin):
    QUALITY_WEIGHTS: ClassVar[dict[str, float]] = {
        "ao": 0,
        "auto": 200,
        "ld": 300,
        "sd": 400,
        "hd": 500,
        "hd_60": 600,
        "uhd": 700,
        "uhd_60": 800,
        "origin": 1000000,
    }

    _URL_API_LIVE = "https://www.tiktok.com/api-live/user/room"

    _STATUS_OFFLINE = 4
    _PROTOCOL_ORDER = {"flv": 10}
    _CODEC_ORDER = {"h264": 1, "h265": 2}

    @classmethod
    def stream_weight(cls, stream: str) -> tuple[float, str]:
        try:
            # protocol, codec, stream = stream.split("_", 2)
            codec, stream = stream.split("_", 1)
            if weight := cls.QUALITY_WEIGHTS.get(stream):
                return weight + cls._PROTOCOL_ORDER.get("flv", 0) + cls._CODEC_ORDER.get(codec, 0), "tiktok"
        except ValueError:
            pass

        return super().stream_weight(stream)

    _SCHEMA_STREAM_DATA = validate.Schema(
        validate.none_or_all(
            str,
            validate.parse_json(),
            {
                "data": {
                    str: validate.all(
                        {
                            "main": {
                                "sdk_params": validate.all(
                                    str,
                                    validate.parse_json(),
                                    {
                                        validate.optional("VCodec"): validate.any(str, None),
                                        validate.optional("v_codec"): validate.any(str, None),
                                    },
                                ),
                                # HLS results in 403 HTTP responses
                                # validate.optional("hls"): validate.any("", validate.url(scheme="https")),
                                validate.optional("flv"): validate.any("", validate.url(scheme="https")),
                            },
                        },
                        validate.get("main"),
                    ),
                },
            },
            validate.get("data"),
        ),
    )

    def _get_stream_data(self, value: str | None, default_codec: str) -> Iterator[tuple[str, Stream]]:
        data: dict[str, dict] | None
        if not (data := self._SCHEMA_STREAM_DATA.validate(value)):
            return

        for quality, stream_data in data.items():
            sdk_params = stream_data["sdk_params"]
            codec = str(sdk_params.get("VCodec") or sdk_params.get("v_codec") or default_codec).lower()
            codec = {"avc": "h264", "hevc": "h265"}.get(codec, codec)

            for protocol in self._PROTOCOL_ORDER:
                # name = f"{protocol}_{codec}_{quality}"
                name = f"{codec}_{quality}"
                if not (url := stream_data.get(protocol, "")):
                    continue

                match protocol:
                    case "flv":
                        yield name, HTTPStream(self.session, url)

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
                        validate.transform(lambda d: (True, d["data"])),
                    ),
                    validate.all(
                        {
                            "message": str,
                        },
                        validate.transform(lambda d: (False, d["message"])),
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
        self.author = author = self.match["channel"]

        data = self._query_api(
            self._URL_API_LIVE,
            params={
                "aid": 1988,
                "sourceType": 54,
                "staleTime": 600000,
                "uniqueId": author.lower(),
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
                                    "stream_data": str,
                                },
                            },
                            validate.get(("pull_data", "stream_data")),
                        ),
                        validate.optional("hevcStreamData"): validate.all(
                            {
                                "pull_data": {
                                    "stream_data": str,
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
                    "hevcStreamData",
                ),
            ),
        )
        if not data:
            return

        status, self.id, self.title, stream_data, hevc_stream_data = data
        if status == self._STATUS_OFFLINE:
            log.info("The channel is currently offline")
            return

        seen = set()
        for quality, stream in [
            *self._get_stream_data(stream_data, "h264"),
            *self._get_stream_data(hevc_stream_data, "h265"),
        ]:
            if quality in seen:
                continue
            seen.add(quality)
            yield quality, stream

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
                                    validate.transform(lambda d: (True, d)),
                                ),
                                validate.all(
                                    {
                                        "statusMsg": str,
                                    },
                                    validate.transform(lambda d: (False, d["statusMsg"])),
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
