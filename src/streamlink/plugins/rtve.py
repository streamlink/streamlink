"""
$description Live TV channels and video on-demand service from RTVE, a Spanish public, state-owned broadcaster.
$url rtve.es
$type live, vod
$metadata id
$region Spain
"""

from __future__ import annotations

import logging
import re
from base64 import b64decode
from collections.abc import Iterator, Sequence
from io import BytesIO
from urllib.parse import urlparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


class Base64Reader:
    def __init__(self, data: str):
        stream = BytesIO(b64decode(data))

        def _iterate():
            while True:
                chunk = stream.read(1)
                if len(chunk) == 0:
                    return
                yield ord(chunk)

        self._iterator: Iterator[int] = _iterate()

    def read(self, num: int) -> Sequence[int]:
        res = []
        for _ in range(num):
            item = next(self._iterator, None)
            if item is None:
                break
            res.append(item)
        return res

    def skip(self, num: int) -> None:
        self.read(num)

    def read_chars(self, num: int) -> str:
        return "".join(chr(item) for item in self.read(num))

    def read_int(self) -> int:
        a, b, c, d = self.read(4)
        return a << 24 | b << 16 | c << 8 | d

    def read_chunk(self) -> tuple[str, Sequence[int]]:
        size = self.read_int()
        chunktype = self.read_chars(4)
        chunkdata = self.read(size)
        if len(chunkdata) != size:  # pragma: no cover
            raise ValueError("Invalid chunk length")
        self.skip(4)
        return chunktype, chunkdata

    def __iter__(self):
        self.skip(8)
        while True:
            try:
                yield self.read_chunk()
            except ValueError:
                return


class ZTNR:
    @staticmethod
    def _get_alphabet(text: str) -> str:
        res = []
        j = 0
        k = 0
        for char in text:
            if k > 0:
                k -= 1
            else:
                res.append(char)
                j = (j + 1) % 4
                k = j
        return "".join(res)

    @staticmethod
    def _get_url(text: str, alphabet: str) -> str:
        res = []
        j = 0
        n = 0
        k = 3
        cont = 0
        for char in text:
            if j == 0:
                n = int(char) * 10
                j = 1
            elif k > 0:
                k -= 1
            else:
                res.append(alphabet[n + int(char)])
                j = 0
                k = cont % 4
                cont += 1
        return "".join(res)

    @classmethod
    def _get_source(cls, alphabet: str, data: str) -> str:
        return cls._get_url(data, cls._get_alphabet(alphabet))

    @classmethod
    def translate(cls, data: str) -> Iterator[tuple[str, str]]:
        reader = Base64Reader(data.replace("\n", ""))
        for chunk_type, chunk_data in reader:
            if chunk_type == "IEND":
                break
            if chunk_type == "tEXt":
                content = "".join(chr(item) for item in chunk_data if item > 0)
                if "#" not in content or "%%" not in content:
                    continue
                alphabet, content = content.split("#", 1)
                quality, content = content.split("%%", 1)
                yield quality, cls._get_source(alphabet, content)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?rtve\.es/play/videos/.+"),
)
class Rtve(Plugin):
    URL_M3U8 = "https://ztnr.rtve.es/ztnr/{id}.m3u8"
    URL_VIDEOS = "https://ztnr.rtve.es/ztnr/movil/thumbnail/rtveplayw/videos/{id}.png?q=v2"
    URL_SUBTITLES = "https://www.rtve.es/api/videos/{id}/subtitulos.json"

    def _get_streams(self):
        self.id = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"\bdata-setup='({.+?})'", re.DOTALL),
                validate.none_or_all(
                    validate.get(1),
                    validate.parse_json(),
                    {
                        "idAsset": validate.any(int, validate.all(str, validate.transform(int))),
                    },
                    validate.get("idAsset"),
                ),
            ),
        )
        if not self.id:
            return

        # check obfuscated stream URLs via self.URL_VIDEOS and ZTNR.translate() first
        # self.URL_M3U8 appears to be valid for all streams, but doesn't provide any content in some cases
        try:
            urls = self.session.http.get(
                self.URL_VIDEOS.format(id=self.id),
                schema=validate.Schema(
                    validate.transform(ZTNR.translate),
                    validate.transform(list),
                    [(str, validate.url())],
                    validate.length(1),
                ),
            )
        except PluginError:
            # catch HTTP errors and validation errors, and fall back to generic HLS URL template
            url = self.URL_M3U8.format(id=self.id)
        else:
            url = next((url for _, url in urls if urlparse(url).path.endswith(".m3u8")), None)
            if not url:
                url = next((url for _, url in urls if urlparse(url).path.endswith(".mp4")), None)
                if url:
                    yield "vod", HTTPStream(self.session, url)
                return

        streams = HLSStream.parse_variant_playlist(self.session, url).items()

        if self.session.get_option("mux-subtitles"):
            subs = self.session.http.get(
                self.URL_SUBTITLES.format(id=self.id),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "page": {
                            "items": [
                                {
                                    "lang": str,
                                    "src": validate.url(),
                                },
                            ],
                        },
                    },
                    validate.get(("page", "items")),
                ),
            )
            if subs:
                subtitles = {
                    s["lang"]: HTTPStream(self.session, update_scheme("https://", s["src"], force=True))
                    for s in subs
                }  # fmt: skip
                for quality, stream in streams:
                    yield quality, MuxedStream(self.session, stream, subtitles=subtitles)
                return

        yield from streams


__plugin__ = Rtve
