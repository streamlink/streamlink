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
from ssl import OP_NO_TICKET

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.session.http import SSLContextAdapter
from streamlink.session.http_useragents import CHROME
from streamlink.stream.hls import HLSStream


class KickAdapter(SSLContextAdapter):
    def get_ssl_context(self):
        ctx = super().get_ssl_context()
        ctx.options &= ~OP_NO_TICKET

        return ctx


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)$"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?:video/|[^/]+/videos/)(?P<vod>[^/?]+)"),
)
@pluginmatcher(
    name="clip",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)\?clip=(?P<clip>[^&]+)$"),
)
class Kick(Plugin):
    _URL_API_LIVESTREAM = "https://kick.com/api/v2/channels/{channel}/livestream"
    _URL_API_VOD = "https://kick.com/api/v1/video/{vod}"
    _URL_API_CLIP = "https://kick.com/api/v2/clips/{clip}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.mount("https://kick.com/", KickAdapter())

        m = re.search(r"Chrome/(?P<full>(?P<main>\d+)\S+)", CHROME)
        if not m:
            raise PluginError("Error while parsing Chromium User-Agent")
        main = m["main"]
        full = m["full"]

        self.session.http.headers.update({
            "User-Agent": CHROME,
            "sec-ch-ua": f'"Not:A-Brand";v="24", "Chromium";v="{main}"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": f'"{full}"',
            "sec-ch-ua-full-version-list": f'"Not:A-Brand";v="24.0.0.0", "Chromium";v="{full}"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"6.14.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
        })

    def _get_api_headers(self):
        return {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "Referer": self.url,
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
