"""
$description Global live-streaming platform owned by BitTorrent, Inc.
$url dlive.tv
$type live, vod
"""

import logging
import re
from urllib.parse import unquote_plus

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?dlive\.tv/
    (?:
        p/(?P<video>[^/]+)
        |
        (?P<channel>[^/]+)
    )
""", re.VERBOSE))
class DLive(Plugin):
    URL_LIVE = "https://live.prd.dlive.tv/hls/live/{username}.m3u8"

    QUALITY_WEIGHTS = {
        "src": 1080,
    }

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "dlive"

        return super().stream_weight(key)

    def _get_streams_video(self, video):
        log.debug(f"Getting video HLS streams for {video}")
        hls_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.regex(re.compile(r'"playbackUrl"\s*:\s*"([^"]+\.m3u8)"')),
            validate.get(1),
            validate.transform(unquote_plus),
            validate.transform(lambda url: bytes(url, "utf-8").decode("unicode_escape")),
            validate.url(),
        ))

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_live(self, channel):
        log.debug(f"Getting live HLS streams for {channel}")
        query = f"""query {{
            userByDisplayName(displayname:"{channel}") {{
                livestream {{
                    title
                }}
                username
            }}
        }}"""
        livestream, username = self.session.http.post(
            "https://graphigo.prd.dlive.tv/",
            json={"query": query},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "userByDisplayName": {
                            "livestream": {
                                "title": str,
                            },
                            "username": str,
                        },
                    },
                },
                validate.get(("data", "userByDisplayName")),
                validate.union_get("livestream", "username"),
            ),
        )

        self.author = channel
        self.title = livestream["title"]

        return HLSStream.parse_variant_playlist(self.session, self.URL_LIVE.format(username=username))

    def _get_streams(self):
        video = self.match.group("video")
        channel = self.match.group("channel")

        if video:
            return self._get_streams_video(video)
        elif channel:
            return self._get_streams_live(channel)


__plugin__ = DLive
