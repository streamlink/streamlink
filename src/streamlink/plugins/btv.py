"""
$description A privately owned Bulgarian live TV channel.
$url btvplus.bg
$type live
$region Bulgaria
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?btvplus\.bg/live/?"
))
class BTV(Plugin):
    URL_API = "https://btvplus.bg/lbin/v3/btvplus/player_config.php"

    def _get_streams(self):
        media_id = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"media_id=(\d+)"),
            validate.any(None, validate.get(1)),
        ))
        if media_id is None:
            return

        stream_url = self.session.http.get(
            self.URL_API,
            params={
                "media_id": media_id,
            },
            schema=validate.Schema(
                validate.any(
                    validate.all(
                        validate.regex(re.compile(r"geo_blocked_stream")),
                        validate.get(0),
                    ),
                    validate.all(
                        validate.parse_json(),
                        {
                            "status": "ok",
                            "config": str,
                        },
                        validate.get("config"),
                        re.compile(r"src: \"(http.*?)\""),
                        validate.none_or_all(
                            validate.get(1),
                            validate.url(),
                        ),
                    ),
                ),
            ),
        )
        if not stream_url:
            return

        if stream_url == "geo_blocked_stream":
            log.error("The content is not available in your region")
            return

        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = BTV
