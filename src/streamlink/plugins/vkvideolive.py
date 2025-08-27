"""
$description Russian live-streaming platform for gaming and esports, owned by VKontakte. Formerly called vkplay.
$url live.vkvideo.ru
$url live.vkplay.ru
$url vkplay.live
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:live\.vk(?:video|play)\.ru|vkplay\.live)/(?P<channel_name>\w+)(?:/?$|(?P<vod>/record/[^?#]+))"),
)
class VKvideolive(Plugin):
    API_URL = "https://api.live.vkvideo.ru/v1"

    _WEIGHTS = {
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    @classmethod
    def stream_weight(cls, stream):
        if stream in cls._WEIGHTS:
            return cls._WEIGHTS[stream], "vkvideolive"

        return super().stream_weight(stream)

    def _query_api(self, channel_name, vod):
        schema_data = validate.all(
            {
                validate.optional("category"): validate.all(
                    {
                        "title": str,
                    },
                    validate.get("title"),
                ),
                "title": str,
                "data": validate.any(
                    [
                        validate.all(
                            {
                                "vid": str,
                                "playerUrls": [
                                    validate.all(
                                        {
                                            "type": str,
                                            "url": validate.any("", validate.url()),
                                        },
                                        validate.union_get("type", "url"),
                                    ),
                                ],
                            },
                            validate.union_get("vid", "playerUrls"),
                        ),
                    ],
                    [],
                ),
            },
            validate.union_get(
                "category",
                "title",
                ("data", 0),
            ),
        )
        schema_response = validate.any(
            validate.all(
                {"error": str, "error_description": str},
                validate.get("error_description"),
            ),
            schema_data,
        )

        if not vod:
            schema = schema_response
        else:
            schema = validate.all(
                {
                    "data": {
                        "record": schema_response,
                    },
                },
                validate.get(("data", "record")),
            )

        data = self.session.http.get(
            f"{self.API_URL}/blog/{channel_name}/public_video_stream{vod}",
            headers={"Referer": self.url},
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                schema,
            ),
        )
        if isinstance(data, str):
            raise PluginError(f"VKvideo API error: {data}")

        return data

    def _get_streams(self):
        self.author = self.match["channel_name"]
        log.debug(f"Channel name: {self.author}")
        vod = self.match["vod"] or ""
        log.debug(f"VOD: {vod}")

        data = self._query_api(channel_name=self.author, vod=vod)

        self.category, self.title, streamdata = data
        if not streamdata:
            return

        self.id, streams = streamdata

        if not vod:
            for streamtype, streamurl in streams:
                if streamurl and streamtype == "live_hls":
                    yield from HLSStream.parse_variant_playlist(self.session, streamurl).items()
        else:
            for streamtype, streamurl in streams:
                if streamurl and streamtype in ("high", "medium", "low"):
                    yield streamtype, HTTPStream(self.session, streamurl)


__plugin__ = VKvideolive
