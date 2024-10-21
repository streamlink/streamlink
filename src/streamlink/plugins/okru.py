"""
$description Russian live-streaming and video hosting social platform.
$url ok.ru
$url mobile.ok.ru
$type live, vod
$metadata id
$metadata author
$metadata title
"""

import logging
import re
from urllib.parse import unquote, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.)?ok\.ru/"),
)
@pluginmatcher(
    name="mobile",
    pattern=re.compile(r"https?://m(?:obile)?\.ok\.ru/"),
)
class OKru(Plugin):
    QUALITY_WEIGHTS = {
        "full": 1080,
        "1080": 1080,
        "hd": 720,
        "720": 720,
        "sd": 480,
        "480": 480,
        "360": 360,
        "low": 360,
        "lowest": 240,
        "mobile": 144,
    }

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "okru"

        return super().stream_weight(key)

    def _get_streams_mobile(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//a[@data-video]"),
                validate.get("data-video"),
                validate.none_or_all(
                    str,
                    validate.parse_json(),
                    {
                        "videoName": str,
                        "videoSrc": validate.url(),
                        "movieId": str,
                    },
                    validate.union_get("movieId", "videoName", "videoSrc"),
                ),
            ),
        )
        if not data:
            return

        self.id, self.title, url = data

        stream_url = self.session.http.head(url).headers.get("Location")
        if not stream_url:
            return

        return (
            HLSStream.parse_variant_playlist(self.session, stream_url)
            if urlparse(stream_url).path.endswith(".m3u8")
            else {"vod": HTTPStream(self.session, stream_url)}
        )

    def _get_streams_default(self):
        schema_metadata = validate.Schema(
            validate.parse_json(),
            {
                validate.optional("author"): validate.all({validate.optional("name"): str}, validate.get("name")),
                validate.optional("movie"): validate.all(
                    {
                        validate.optional("id"): str,
                        validate.optional("title"): str,
                    },
                    validate.union_get("id", "title"),
                ),
                validate.optional("hlsManifestUrl"): validate.url(),
                validate.optional("hlsMasterPlaylistUrl"): validate.url(),
                validate.optional("liveDashManifestUrl"): validate.url(),
                validate.optional("videos"): [
                    validate.all(
                        {
                            "name": str,
                            "url": validate.url(),
                        },
                        validate.union_get("name", "url"),
                    ),
                ],
            },
        )

        metadata, metadata_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//*[@data-options]"),
                validate.get("data-options"),
                validate.parse_json(),
                {
                    "flashvars": {
                        validate.optional("metadata"): str,
                        validate.optional("metadataUrl"): validate.all(
                            validate.transform(unquote),
                            validate.url(),
                        ),
                    },
                },
                validate.get("flashvars"),
                validate.union_get("metadata", "metadataUrl"),
            ),
        )

        self.session.http.headers.update({"Referer": self.url})

        if not metadata and metadata_url:
            metadata = self.session.http.post(metadata_url).text

        log.trace(f"{metadata!r}")

        data = schema_metadata.validate(metadata)

        self.author = data.get("author")
        self.id, self.title = data.get("movie", (None, None))

        for hls_url in data.get("hlsManifestUrl"), data.get("hlsMasterPlaylistUrl"):
            if hls_url is not None:
                return HLSStream.parse_variant_playlist(self.session, hls_url)

        if data.get("liveDashManifestUrl"):
            return DASHStream.parse_manifest(self.session, data.get("liveDashManifestUrl"))

        return {
            f"{self.QUALITY_WEIGHTS[name]}p" if name in self.QUALITY_WEIGHTS else name: HTTPStream(self.session, url)
            for name, url in data.get("videos", [])
        }

    def _get_streams(self):
        return self._get_streams_default() if self.matches["default"] else self._get_streams_mobile()


__plugin__ = OKru
