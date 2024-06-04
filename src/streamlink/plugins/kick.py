"""
$description Global live-streaming and video hosting social platform owned by Kick Streaming Pty Ltd.
$url kick.com
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)$"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/video/(?P<vod>[^/?]+)"),
)
@pluginmatcher(
    name="clip",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)\?clip=(?P<clip>[^&]+)$"),
)
class Kick(Plugin):
    _URL_TOKEN = "https://kick.com/"
    _URL_API_LIVESTREAM = "https://kick.com/api/v2/channels/{channel}/livestream"
    _URL_API_VOD = "https://kick.com/api/v1/video/{vod}"
    _URL_API_CLIP = "https://kick.com/api/v2/clips/{clip}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token = ""

    def _get_api_headers(self):
        accept_language = self.session.localization.language_code.replace("_", "-")
        self.session.http.headers.update({"Accept-Language": accept_language})

        self._token = (
            self._token
            or self.session.http.get(self._URL_TOKEN, raise_for_status=False).cookies.get("XSRF-TOKEN", "")
        )

        return {
            "Accept": "application/json",
            "Referer": self.url,
            "Authorization": f"Bearer {self._token}",
        }

    def _get_streams_live(self):
        self.author = self.match["channel"]

        data = self.session.http.get(
            self._URL_API_LIVESTREAM.format(channel=self.author),
            acceptable_status=(200, 404),
            headers=self._get_api_headers(),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"message": str},
                        validate.transform(lambda _: None),
                    ),
                    validate.all(
                        {"data": None},
                        validate.transform(lambda _: None),
                    ),
                    validate.all(
                        {
                            "data": {
                                "playback_url": validate.url(path=validate.endswith(".m3u8")),
                                "id": int,
                                "category": {"name": str},
                                "session_title": str,
                            },
                        },
                        validate.get("data"),
                        validate.union_get(
                            "playback_url",
                            "id",
                            ("category", "name"),
                            "session_title",
                        ),
                    ),
                ),
            ),
        )
        if not data:
            return

        hls_url, self.id, self.category, self.title = data

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_vod(self):
        self.id = self.match["vod"]

        data = self.session.http.get(
            self._URL_API_VOD.format(vod=self.id),
            acceptable_status=(200, 404),
            headers=self._get_api_headers(),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"message": str},
                        validate.transform(lambda _: None),
                    ),
                    validate.all(
                        {
                            "source": validate.url(path=validate.endswith(".m3u8")),
                            "livestream": {
                                "session_title": str,
                                "channel": {
                                    "user": {
                                        "username": str,
                                    },
                                },
                            },
                        },
                        validate.union_get(
                            "source",
                            ("livestream", "channel", "user", "username"),
                            ("livestream", "session_title"),
                        ),
                    ),
                ),
            ),
        )
        if not data:
            return

        hls_url, self.author, self.title = data

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_clip(self):
        self.id = self.match["clip"]
        self.author = self.match["channel"]

        data = self.session.http.get(
            self._URL_API_CLIP.format(clip=self.id),
            acceptable_status=(200, 404),
            headers=self._get_api_headers(),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"message": str},
                        validate.transform(lambda _: None),
                    ),
                    validate.all(
                        {"clip": None},
                        validate.transform(lambda _: None),
                    ),
                    validate.all(
                        {
                            "clip": {
                                "clip_url": validate.url(path=validate.endswith(".m3u8")),
                                "category": {"name": str},
                                "title": str,
                            },
                        },
                        validate.get("clip"),
                        validate.union_get(
                            "clip_url",
                            ("category", "name"),
                            "title",
                        ),
                    ),
                ),
            ),
        )
        if not data:
            return

        hls_url, self.category, self.title = data

        return {"clip": HLSStream(self.session, hls_url)}

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_streams_live()
        if self.matches["vod"]:
            return self._get_streams_vod()
        if self.matches["clip"]:
            return self._get_streams_clip()


__plugin__ = Kick
