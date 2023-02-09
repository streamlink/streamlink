"""
$description Spanish live TV channels from Atresmedia Television, including Antena 3 and laSexta.
$url atresplayer.com
$type live
$region Spain
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?atresplayer\.com/",
))
class AtresPlayer(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = update_scheme("https://", f"{self.url.rstrip('/')}/")

    def _get_streams(self):
        path = urlparse(self.url).path
        api_url = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""window.__PRELOADED_STATE__\s*=\s*({.*?});""", re.DOTALL),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                {"links": {path: {"href": validate.url()}}},
                validate.get(("links", path, "href")),
            ),
        ))
        if not api_url:
            return
        log.debug(f"API URL: {api_url}")

        player_api_url = self.session.http.get(api_url, schema=validate.Schema(
            validate.parse_json(),
            {"urlVideo": validate.url()},
            validate.get("urlVideo"),
        ))

        log.debug(f"Player API URL: {player_api_url}")
        sources = self.session.http.get(player_api_url, acceptable_status=(200, 403), schema=validate.Schema(
            validate.parse_json(),
            validate.any(
                {
                    "error": str,
                    "error_description": str,
                },
                {
                    "sources": [
                        validate.all(
                            {
                                "src": validate.url(),
                                validate.optional("type"): str,
                            },
                            validate.union_get("type", "src"),
                        ),
                    ],
                },
            ),
        ))
        if "error" in sources:
            log.error(f"Player API error: {sources['error']} - {sources['error_description']}")
            return

        for streamtype, streamsrc in sources.get("sources"):
            log.debug(f"Stream source: {streamsrc} ({streamtype or 'n/a'})")

            if streamtype == "application/vnd.apple.mpegurl":
                streams = HLSStream.parse_variant_playlist(self.session, streamsrc)
                if not streams:
                    yield "live", HLSStream(self.session, streamsrc)
                else:
                    yield from streams.items()
            elif streamtype == "application/dash+xml":
                yield from DASHStream.parse_manifest(self.session, streamsrc).items()


__plugin__ = AtresPlayer
