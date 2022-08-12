"""
$description Spanish live TV channels from Atresmedia Television, including Antena 3 and laSexta.
$url atresplayer.com
$type live
$region Spain
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.data import search_dict
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?atresplayer\.com/"
))
class AtresPlayer(Plugin):
    def _get_streams(self):
        self.url = update_scheme("https://", self.url)

        api_url = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""window.__PRELOADED_STATE__\s*=\s*({.*?});""", re.DOTALL),
            validate.none_or_all(
                validate.get(1),
                validate.parse_json(),
                validate.transform(search_dict, key="href"),
                [validate.url()],
                validate.get(0),
            ),
        ))
        if not api_url:
            return
        log.debug("API URL: {0}".format(api_url))

        player_api_url = self.session.http.get(api_url, schema=validate.Schema(
            validate.parse_json(),
            validate.transform(search_dict, key="urlVideo"),
        ))

        stream_schema = validate.Schema(
            validate.parse_json(),
            {
                "sources": [
                    validate.all(
                        {
                            "src": validate.url(),
                            validate.optional("type"): validate.text,
                        },
                    ),
                ],
            },
            validate.get("sources"),
        )

        for api_url in player_api_url:
            log.debug("Player API URL: {0}".format(api_url))
            for source in self.session.http.get(api_url, schema=stream_schema):
                log.debug("Stream source: {0} ({1})".format(source['src'], source.get('type', 'n/a')))

                if "type" not in source or source["type"] == "application/vnd.apple.mpegurl":
                    streams = HLSStream.parse_variant_playlist(self.session, source["src"])
                    if not streams:
                        yield "live", HLSStream(self.session, source["src"])
                    else:
                        for s in streams.items():
                            yield s
                elif source["type"] == "application/dash+xml":
                    for s in DASHStream.parse_manifest(self.session, source["src"]).items():
                        yield s


__plugin__ = AtresPlayer
