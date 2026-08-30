"""
$description Chinese live-streaming platform owned by ByteDance.
$url live.douyin.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import re
import sys
import uuid

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:live\.)?douyin\.com/(?P<room_id>[^/?]+)",
    ),
)
class Douyin(Plugin):
    _STATUS_LIVE = 2

    # There's no bitrate information in the JSON data available anymore.
    # These weights are based on empirically measured video bitrates of a specific stream during plugin fixing.
    # The values themselves don't matter, only the order.
    QUALITY_WEIGHTS: dict[str, int] = {
        "full_hd1": sys.maxsize,
        "hd1": 8000,
        "sd2": 2000,
        "sd1": 1000,
    }

    @classmethod
    def stream_weight(cls, stream: str) -> tuple[float, str]:
        weight = cls.QUALITY_WEIGHTS.get(stream)
        if weight:
            return weight, stream

        return super().stream_weight(stream)

    SCHEMA_ROOM_STORE = validate.all(
        {
            "roomInfo": {
                validate.optional("room"): validate.all(
                    {
                        "status": int,
                        "id_str": str,
                        "title": str,
                        validate.optional("owner"): validate.all(
                            {"nickname": str},
                            validate.get("nickname"),
                        ),
                        validate.optional("stream_url"): {
                            "flv_pull_url": {
                                str: validate.url(),
                            },
                        },
                    },
                    validate.union_get(
                        "status",
                        "id_str",
                        "title",
                        "owner",
                        "stream_url",
                    ),
                ),
            },
        },
        validate.get(("roomInfo", "room")),
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
                    },
                    validate.get("roomStore"),
                ),
            ),
        )
        if not data:
            return

        status, self.id, self.title, self.author, streams = data
        if status != self._STATUS_LIVE:
            log.info("The channel is currently offline")
            return

        for name, flv_url in streams["flv_pull_url"].items():
            yield name.lower(), HTTPStream(self.session, update_scheme("https://", flv_url, force=True))


__plugin__ = Douyin
