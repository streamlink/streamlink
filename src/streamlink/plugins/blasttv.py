"""
$description Esports tournaments run by BlastTV, based in Denmark.
$url blast.tv
$type live, vod
$metadata id
$metadata title
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    name="live",
    pattern=re.compile(r"^https?://(?:www\.)?blast\.tv(?:/?$|/live(?:/(?P<channel>[a-z0-9_-]+))?)"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"^https?://(?:www\.)?blast\.tv/(?P<game>[^/]+)/tournaments/[^/]+/match/(?P<shortid>\w+)/"),
)
class BlastTv(Plugin):
    _URL_API_LIVE = "https://api.blast.tv/v1/broadcasts/live"
    _URL_API_MATCHES = "https://api.blast.tv/v2/games/{game}/matches/{shortid}"
    _URL_API_REWATCH = "https://api.blast.tv/v1/videos/rewatch/{id}"

    def _get_live(self):
        channel = self.match["channel"]

        live_channels = self.session.http.get(
            self._URL_API_LIVE,
            schema=validate.Schema(
                validate.parse_json(),
                [
                    {
                        "id": str,
                        "slug": str,
                        "priority": int,
                        "title": str,
                        "videoSrc": validate.any("", validate.url(path=validate.endswith(".m3u8"))),
                        "videoAlternativeSrc": validate.any("", validate.url(scheme="http")),
                    },
                ],
            ),
        )

        for live_channel in sorted(live_channels, key=lambda x: x["priority"]):
            if channel and channel != live_channel["slug"]:
                continue

            if live_channel["videoSrc"]:
                self.id = live_channel["id"]
                self.title = live_channel["title"]
                return HLSStream.parse_variant_playlist(self.session, live_channel["videoSrc"])

            if live_channel["videoAlternativeSrc"]:
                return self.session.streams(live_channel["videoAlternativeSrc"])

    def _get_vod(self):
        self.id, external_stream_url = self.session.http.get(
            self._URL_API_MATCHES.format(
                game=self.match["game"],
                shortid=self.match["shortid"],
            ),
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("id"): str,
                    validate.optional("metadata"): validate.all(
                        {
                            validate.optional("externalStreamUrl"): validate.any("", validate.url(scheme="http")),
                        },
                        validate.get("externalStreamUrl"),
                    ),
                },
                validate.union_get(
                    "id",
                    "metadata",
                ),
            ),
        )
        if not self.id:
            return

        if external_stream_url:
            return self.session.streams(external_stream_url)

        hls_url = self.session.http.get(
            self._URL_API_REWATCH.format(id=self.id),
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("src"): validate.url(path=validate.endswith(".m3u8")),
                },
                validate.get("src"),
            ),
        )
        if not hls_url:
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_live()
        if self.matches["vod"]:
            return self._get_vod()


__plugin__ = BlastTv
