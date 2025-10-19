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
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.times import fromtimestamp, now


log = logging.getLogger(__name__)


class DLiveHLSStream(HLSStream):
    URL_SIGN = "https://live.prd.dlive.tv/hls/sign/url"
    URL_KEY_EXPIRES = "Expires"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unsigned_url = self.args["url"]
        self.signed_url = ""
        self.signed_url_expires = fromtimestamp(timestamp=0)

    @property
    def url(self):
        if self.signed_url_expires < now():
            log.debug("Getting new signed HLS playlist URL")
            self.signed_url = self._get_signed_url()
            params = dict(parse_qsl(urlparse(self.signed_url).query))
            expires = int(params.get(self.URL_KEY_EXPIRES, "0"))
            self.signed_url_expires = fromtimestamp(timestamp=expires)

        return self.signed_url

    def _get_signed_url(self):
        return self.session.http.post(
            self.URL_SIGN,
            json={"playlisturi": self.unsigned_url},
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
