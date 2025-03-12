"""
$description Global live-streaming platform owned by BitTorrent, Inc.
$url dlive.tv
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re
from textwrap import dedent

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


class DLiveHLSStream(HLSStream):
    URL_SIGN = "https://live.prd.dlive.tv/hls/sign/url"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args["url"] = self.session.http.post(
            self.URL_SIGN,
            json={"playlisturi": self.args["url"]},
            schema=validate.Schema(validate.url()),
        )


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:www\.)?dlive\.tv/(?P<channel>[^/?#]+)(?:$|[?#])",
    ),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(
        r"https?://(?:www\.)?dlive\.tv/p/(?P<video>[^/?#]+)(?:$|[?#])",
    ),
)
class DLive(Plugin):
    URL_API = "https://graphigo.prd.dlive.tv/"
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

        self.id = video
        hls_url, self.author, self.category, self.title = self.session.http.post(
            self.URL_API,
            json={
                "query": dedent(f"""
                    query {{
                        pastBroadcast(permlink:"{video}") {{
                            playbackUrl
                            creator {{
                                username
                            }}
                            category {{
                                title
                            }}
                            title
                        }}
                    }}
                """),
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "pastBroadcast": {
                            "playbackUrl": validate.url(path=validate.endswith(".m3u8")),
                            "creator": {
                                "username": str,
                            },
                            "category": {
                                "title": str,
                            },
                            "title": str,
                        },
                    },
                },
                validate.get(("data", "pastBroadcast")),
                validate.union_get(
                    "playbackUrl",
                    ("creator", "username"),
                    ("category", "title"),
                    "title",
                ),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_live(self, channel):
        log.debug(f"Getting live HLS streams for {channel}")

        self.author = channel
        username, self.title = self.session.http.post(
            self.URL_API,
            json={
                "query": dedent(f"""
                    query {{
                        userByDisplayName(displayname:"{channel}") {{
                            username
                            livestream {{
                                title
                            }}
                        }}
                    }}
                """),
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "userByDisplayName": {
                            "username": str,
                            "livestream": {
                                "title": str,
                            },
                        },
                    },
                },
                validate.get(("data", "userByDisplayName")),
                validate.union_get(
                    "username",
                    ("livestream", "title"),
                ),
            ),
        )

        return DLiveHLSStream.parse_variant_playlist(self.session, self.URL_LIVE.format(username=username))

    def _get_streams(self):
        self.session.http.headers.update({
            "Origin": "https://dlive.tv",
            "Referer": "https://dlive.tv/",
        })

        if self.matches["live"]:
            return self._get_streams_live(self.match["channel"])
        if self.matches["vod"]:
            return self._get_streams_video(self.match["video"])


__plugin__ = DLive
