"""
$description Global live-streaming platform for live video game broadcasts and individual live streams.
$url bigo.tv
$type live
$metadata id
$metadata author
$metadata category
$metadata title
"""

from __future__ import annotations

import ctypes
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSSegment, HLSStream, M3U8Parser, parse_tag


if TYPE_CHECKING:
    from collections.abc import Iterator

    from requests import Response


log = getLogger(__name__)


@dataclass(kw_only=True)
class BigoHLSSegment(HLSSegment):
    seed: int | None = None

    def iter_content(self, response: Response, chunk_size: int) -> Iterator[bytes]:
        iterator = response.iter_content(chunk_size)
        if self.seed is None:  # pragma: no cover
            yield from iterator
            return

        # allocate data for two MPEG-TS packets
        packets = bytearray(376)
        view = memoryview(packets)
        filled = 0
        remainder = b""

        # read packet contents, keep the remainder and the iterator
        for chunk in iterator:  # pragma: no branch
            needed = 376 - filled
            if len(chunk) <= needed:
                view[filled : filled + len(chunk)] = chunk
                filled += len(chunk)
                if filled == 376:
                    break
            else:
                view[filled:376] = chunk[:needed]
                remainder = chunk[needed:]
                break

        self._decrypt_packets(packets, self.seed)

        yield bytes(packets)
        yield remainder
        yield from iterator

    @staticmethod
    def _decrypt_packets(packets: bytearray, seed: int):
        # translated to Python from their obfuscated JS
        for num in range(2):
            imul = ctypes.c_uint32((num + 1) * 2654435769).value
            r = ctypes.c_uint32(seed ^ imul).value

            if r == 0:
                r = 1831565813

            packet_offset = 188 * num
            for offset in range(16):
                r ^= ctypes.c_uint32(r << 13).value
                r ^= r >> 17
                r ^= ctypes.c_uint32(r << 5).value
                r = ctypes.c_uint32(r).value

                mask = r & 0xFF
                if mask == 0:
                    mask = 165

                packets[packet_offset + offset] ^= mask


class BigoM3U8Parser(M3U8Parser):
    __segment__ = BigoHLSSegment

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.seed: int | None = None

    @parse_tag("EXT-X-BIGO-WEB-PROTECTION")
    def parse_bigo_web_protection(self, value):
        attributes = self.parse_attributes(value)
        try:
            self.seed = int(attributes.get("SEED", -1))
        except ValueError:  # pragma: no cover
            log.warning("Could not parse SEED value of BIGO-WEB-PROTECTION data")

    def get_segment(self, uri: str, **data):
        return super().get_segment(uri, seed=self.seed, **data)


class BigoHLSStream(HLSStream):
    __parser__ = BigoM3U8Parser


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?bigo\.tv/(?P<site_id>[^/]+)$"),
)
class Bigo(Plugin):
    _URL_API = "https://ta.bigo.tv/official_website/studio/getInternalStudioInfo"

    def _get_streams(self):
        self.id, self.author, self.category, self.title, hls_url = self.session.http.post(
            self._URL_API,
            params={
                "siteId": self.match["site_id"],
                "verify": "",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "roomId": validate.any(None, str),
                        "clientBigoId": validate.any(None, str),
                        "gameTitle": str,
                        "roomTopic": str,
                        "hls_src": validate.any(None, "", validate.url()),
                    },
                },
                validate.union_get(
                    ("data", "roomId"),
                    ("data", "clientBigoId"),
                    ("data", "gameTitle"),
                    ("data", "roomTopic"),
                    ("data", "hls_src"),
                ),
            ),
        )

        if not self.id:
            return

        if not hls_url:
            log.info("Channel is offline")
            return

        yield "live", BigoHLSStream(self.session, hls_url)


__plugin__ = Bigo
