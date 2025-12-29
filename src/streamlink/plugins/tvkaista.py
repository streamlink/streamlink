"""
$description Finnish live TV streaming website.
$url tvkaista.org
$type live
"""

import base64
import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:www\.)?tvkaista\.org/(?P<channel>[^/]+)/suora(?:$|[?#])",
    ),
)
class TVKaista(Plugin):
    def _get_streams(self):
        # 1. Mimic a real browser (anti-bot bypass)
        # The site serves a "Lite" page without streams to non-browser User-Agents.

        self.session.http.headers.update(
            {
                "User-Agent": useragents.CHROME,
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        log.debug(f"Fetching HTML for: {self.url}")
        res = self.session.http.get(self.url)

        # 2. Extract ALL hidden Base64 URLs
        # The site hides the real stream URLs inside window.atob("...") calls in the JS.

        b64_matches = re.findall(
            r'window\.atob\(\s*["\']([a-zA-Z0-9+/=]+)["\']\s*\)', res.text
        )

        found_urls = set()

        for b64_str in b64_matches:
            try:
                decoded = base64.b64decode(b64_str).decode("utf-8")

                # SKIP broken streams:
                # 2a. "chromecast" (results in connection timeouts)
                # 2b. "/live" (P2P stream containing 302 Redirect traps to dead servers)

                if "chromecast" in decoded or "/live" in decoded:
                    continue
                if "http" in decoded and ".m3u8" in decoded:
                    if decoded.endswith("tz="):
                        # The JS dynamically appends the client timezone.
                        # We append a default to complete the URL parameters.

                        decoded += "Europe-Helsinki"
                    found_urls.add(decoded)
            except Exception:
                continue
        if not found_urls:
            log.error("No valid hidden streams found (native/legacy).")
            return
        # 3. Yield streams

        for stream_url in found_urls:
            # Name the stream based on its type

            if "native" in stream_url:
                # "native" is standard HLS intended for iOS/Safari (avoids P2P issues)

                name = "native"
            elif "legacy" in stream_url:
                name = "legacy"
            elif "airplay" in stream_url:
                name = "airplay"
            else:
                name = "other"
            log.debug(f"Checking stream ({name}): {stream_url}")

            try:
                # Attempt to parse as Master Playlist (variants)

                streams = HLSStream.parse_variant_playlist(
                    self.session,
                    stream_url,
                    headers={"Referer": self.url},
                )

                if streams:
                    for s_name, s_stream in streams.items():
                        yield f"{name}_{s_name}", s_stream
                else:
                    # Fallback for Media Playlists (Direct Stream)

                    yield name, HLSStream(
                        self.session,
                        stream_url,
                        headers={"Referer": self.url},
                    )

                    # FORCE 'best' alias for the native stream
                    # Native is usually the highest quality and most reliable (non-P2P).

                    if name == "native":
                        yield "best", HLSStream(
                            self.session,
                            stream_url,
                            headers={"Referer": self.url},
                        )
            except Exception as e:
                log.warning(f"Skipping unplayable stream '{name}': {e}")


__plugin__ = TVKaista
