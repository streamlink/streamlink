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

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.session.http import SSLContextAdapter
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
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)(?:\?clip=|/clips/)(?P<clip>[^?&]+)"),
)
class Kick(Plugin):
    _URL_API_LIVESTREAM = "https://kick.com/api/v2/channels/{channel}/livestream"
    _URL_API_VOD = "https://kick.com/api/v1/video/{vod}"
    _URL_API_CLIP = "https://kick.com/api/v2/clips/{clip}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.mount("https://kick.com/", KickAdapter())
        self.session.http.headers.update({
            "Referer": self.url,
            "User-Agent": useragents.CHROME,
        })

    @staticmethod
    def _get_api_headers():
        if not (m := re.search(r"Chrome/(?P<full>(?P<main>\d+)\S+)", useragents.CHROME)):
            raise PluginError("Error while parsing Chromium User-Agent")

        return {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "sec-ch-ua": f'"Not:A-Brand";v="24", "Chromium";v="{m["main"]}"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": f'"{m["full"]}"',
            "sec-ch-ua-full-version-list": f'"Not:A-Brand";v="24.0.0.0", "Chromium";v="{m["full"]}"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"6.14.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
        }

    def _query_api(self, url, schema):
        schema = validate.Schema(
            validate.parse_json(),
            validate.any(
                validate.all(
                    {"message": str},
                    validate.transform(lambda obj: ("error", obj["message"])),
                ),
                validate.all(
                    {"data": None},
                    validate.transform(lambda _: ("data", None)),
                ),
                validate.all(
                    schema,
                    validate.transform(lambda obj: ("data", obj)),
                ),
            ),
        )

        res = self.session.http.get(
            url,
            headers=self._get_api_headers(),
            raise_for_status=False,
        )
        if res.status_code == 403:
            raise PluginError("Error while accessing Kick API: status code 403")

        restype, data = schema.validate(res.text)

        if restype == "error":
            raise PluginError(f"Error while querying Kick API: {data or 'unknown error'}")
        if not data:
            raise NoStreamsError

        return data

    def _get_streams_live(self):
        self.author = self.match["channel"]

        hls_url, self.id, self.category, self.title = self._query_api(
            self._URL_API_LIVESTREAM.format(channel=self.author),
            schema=validate.Schema(
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
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_vod(self):
        self.id = self.match["vod"]

        hls_url, self.author, self.title = self._query_api(
            self._URL_API_VOD.format(vod=self.id),
            schema=validate.Schema(
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
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_clip(self):
        self.id = self.match["clip"]
        self.author = self.match["channel"]

        hls_url, self.category, self.title = self._query_api(
            self._URL_API_CLIP.format(clip=self.id),
            schema=validate.Schema(
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
        )

        return {"clip": HLSStream(self.session, hls_url)}

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_streams_live()
        if self.matches["vod"]:
            return self._get_streams_vod()
        if self.matches["clip"]:
            return self._get_streams_clip()


__plugin__ = Kick
