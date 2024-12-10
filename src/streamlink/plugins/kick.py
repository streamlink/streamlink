"""
$description Global live-streaming and video hosting social platform owned by Kick Streaming Pty Ltd.
$url kick.com
$type live, vod
$webbrowser Required for solving a JS challenge that allows access to the Kick API
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re
from ssl import OP_NO_TICKET

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.session.http import SSLContextAdapter
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


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
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/video/(?P<vod>[^/?]+)"),
)
@pluginmatcher(
    name="clip",
    pattern=re.compile(r"https?://(?:\w+\.)?kick\.com/(?!video/)(?P<channel>[^/?]+)\?clip=(?P<clip>[^&]+)$"),
)
class Kick(Plugin):
    _TOKEN_NAME = "XSRF-TOKEN"
    _TOKEN_EXPIRATION = 3600 * 24 * 30

    _URL_API_CHECK_TOKEN = "https://kick.com/api/v1/categories/top"
    _URL_API_LIVESTREAM = "https://kick.com/api/v2/channels/{channel}/livestream"
    _URL_API_VOD = "https://kick.com/api/v1/video/{vod}"
    _URL_API_CLIP = "https://kick.com/api/v2/clips/{clip}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.mount("https://kick.com/", KickAdapter())
        self._token = self.cache.get(self._TOKEN_NAME)

    def _get_api_headers(self):
        return {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "Referer": self.url,
            "Authorization": f"Bearer {self._token}",
        }

    def _check_token(self):
        if not self._token:
            return False

        res = self.session.http.get(
            self._URL_API_CHECK_TOKEN,
            headers=self._get_api_headers(),
            raise_for_status=False,
        )
        if 400 <= res.status_code < 500:
            self.cache.set(self._TOKEN_NAME, None, expires=0)
            return False

        log.debug("Using cached JS challenge token")

        return True

    def _get_token(self):
        from streamlink.compat import BaseExceptionGroup  # noqa: PLC0415
        from streamlink.webbrowser.cdp import CDPClient, CDPClientSession  # noqa: PLC0415

        eval_timeout = self.session.get_option("webbrowser-timeout")

        async def get_challenge_cookies(client: CDPClient):
            client_session: CDPClientSession
            async with client.session() as client_session:
                async with client_session.navigate(self.url) as frame_id:
                    await client_session.loaded(frame_id)
                    return await client_session.evaluate("document.cookie", timeout=eval_timeout)

        log.info("Solving JS challenge using webbrowser API")

        cookiestring = ""
        try:
            cookiestring = CDPClient.launch(self.session, get_challenge_cookies)
        except BaseExceptionGroup:
            log.exception("Failed solving JS challenge")
        except Exception as err:
            log.error(err)

        cookies = dict(cookie.split("=", 1) for cookie in cookiestring.split("; "))
        self._token = cookies.get(self._TOKEN_NAME)

        if self._token:
            self.cache.set(self._TOKEN_NAME, self._token, expires=self._TOKEN_EXPIRATION)

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
        if not self._check_token():
            self._get_token()

        if self.matches["live"]:
            return self._get_streams_live()
        if self.matches["vod"]:
            return self._get_streams_vod()
        if self.matches["clip"]:
            return self._get_streams_clip()


__plugin__ = Kick
