"""
$description Chinese live-streaming platform owned by ByteDance.
$url live.douyin.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import logging
import re
import uuid

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:live\.)?douyin\.com/(?P<room_id>[^/?]+)",
    ),
)
class Douyin(Plugin):
    _STATUS_LIVE = 2

    QUALITY_WEIGHTS: dict[str, int] = {}

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, key

        return super().stream_weight(key)

    SCHEMA_ROOM_STORE = validate.all(
        {
            "roomInfo": {
                # "room" and "anchor" keys are missing on invalid channels
                validate.optional("room"): validate.all(
                    {
                        "id_str": str,
                        "status": int,
                        "title": str,
                    },
                    validate.union_get(
                        "status",
                        "id_str",
                        "title",
                    ),
                ),
                validate.optional("anchor"): validate.all(
                    {"nickname": str},
                    validate.get("nickname"),
                ),
            },
        },
        validate.union_get(
            ("roomInfo", "room"),
            ("roomInfo", "anchor"),
        ),
    )

    SCHEMA_STREAM_STORE = validate.all(
        {
            "streamData": {
                "H264_streamData": {
                    # "stream" value is `none` on offline/invalid channels
                    "stream": validate.none_or_all(
                        {
                            str: validate.all(
                                {
                                    "main": {
                                        # HLS stream URLs are multivariant streams but only with a single media playlist,
                                        # so avoid using HLS in favor of having reduced stream lookup/start times
                                        "flv": validate.any("", validate.url()),
                                        "sdk_params": validate.all(
                                            validate.parse_json(),
                                            {"vbitrate": int},
                                            validate.get("vbitrate"),
                                        ),
                                    },
                                },
                                validate.union_get(
                                    ("main", "sdk_params"),
                                    ("main", "flv"),
                                ),
                            ),
                        },
                    ),
                },
            },
        },
        validate.get(("streamData", "H264_streamData", "stream")),
    )

    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            cookies={
                "__ac_nonce": uuid.uuid4().hex[:21],
            },
            schema=validate.Schema(
                validate.regex(
                    pattern=re.compile(r"self\.__pace_f\.push\(\[\d+,(\"\w+:.+?\")]\)</script>"),
                    method="findall",
                ),
                validate.filter(lambda item: "state" in item and "streamStore" in item),
                validate.get(-1),
                validate.none_or_all(
                    validate.parse_json(),
                    validate.transform(lambda s: re.sub(r"^\w+:", "", s)),
                    validate.parse_json(),
                    list,
                    validate.filter(lambda item: isinstance(item, dict) and "state" in item),
                    validate.length(1),
                    validate.get((0, "state")),
                    {
                        "roomStore": self.SCHEMA_ROOM_STORE,
                        "streamStore": self.SCHEMA_STREAM_STORE,
                    },
                    validate.union_get(
                        "roomStore",
                        "streamStore",
                    ),
                ),
            ),
        )
        if not data:
            return

        (room_info, self.author), stream_data = data
        if not room_info:
            return

        status, self.id, self.title = room_info
        if status != self._STATUS_LIVE:
            log.info("The channel is currently offline")
            return

        for name, (vbitrate, url) in stream_data.items():
            if not url:
                continue
            self.QUALITY_WEIGHTS[name] = vbitrate
            url = update_scheme("https://", url, force=True)
            yield name, HTTPStream(self.session, url)

        log.debug(f"{self.QUALITY_WEIGHTS=!r}")


__plugin__ = Douyin
