"""
$description Spanish live TV channels from Atresmedia Television, including Antena 3 and laSexta.
$url atresplayer.com
$type live
$region Spain
"""

import logging
import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?atresplayer\.com/"
))
class AtresPlayer(Plugin):
    def _get_streams(self):
        self.url = update_scheme("https://", self.url)
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
        log.debug("API URL: {0}".format(api_url))

        player_api_url = self.session.http.get(api_url, schema=validate.Schema(
            validate.parse_json(),
            {"urlVideo": validate.url()},
            validate.get("urlVideo"),
        ))

        log.debug("Player API URL: {0}".format(player_api_url))
        sources = self.session.http.get(player_api_url, acceptable_status=(200, 403), schema=validate.Schema(
            validate.parse_json(),
            validate.any(
                {
                    "error": validate.text,
                    "error_description": validate.text,
                },
                {
                    "sources": [
                        validate.all(
                            {
                                "src": validate.url(),
                                validate.optional("type"): validate.text,
                            },
                            validate.union_get("type", "src"),
                        ),
                    ],
                },
            ),
        ))
        if "error" in sources:
            log.error("Player API error: {0} - {1}".format(sources['error'], sources['error_description']))
            return

        for streamtype, streamsrc in sources.get("sources"):
            log.debug("Stream source: {0} ({1})".format(streamsrc, streamtype or 'n/a'))

            if streamtype == "application/vnd.apple.mpegurl":
                streams = HLSStream.parse_variant_playlist(self.session, streamsrc)
                if not streams:
                    yield "live", HLSStream(self.session, streamsrc)
                else:
                    for s in streams.items():
                        yield s
            elif streamtype == "application/dash+xml":
                for s in DASHStream.parse_manifest(self.session, streamsrc).items():
                    yield s


__plugin__ = AtresPlayer
