"""
$description Live TV channels from RAI, an Italian public, state-owned broadcaster.
$url raiplay.it
$type live, vod
$region Italy
"""

import base64
import logging
import re
from urllib.parse import parse_qsl, urlparse, urlunparse

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.times import fromtimestamp
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:www\.)?raiplay\.it/dirette/(\w+)/?",
    ),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(
        r"https?://(?:www\.)?raiplay\.it/video/.+",
    ),
)
@pluginargument(
    "email",
    requires=["password"],
    metavar="EMAIL",
    help="The email used to register with raiplay.it.",
)
@pluginargument(
    "password",
    prompt="Enter raiplay.it account password",
    sensitive=True,
    metavar="PASSWORD",
    help="A raiplay.it account password to use with --raiplay-email.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached RaiPlay credentials to initiate a new session and reauthenticate.",
)
class RaiPlay(Plugin):
    _DEFAULT_MEDIAPOLIS_OUTPUT = "64"
    _AUTH_URL = "https://www.raiplay.it/raisso/login/domain/app/social"
    _DOMAIN_API_KEY = "arSgRtwasD324SaA"
    _CACHE_KEY_UA_TOKEN = "ua-token"

    def _get_streams(self):
        if self.options.get("purge-credentials"):
            log.info("Removing cached user-authentication token...")
            self.cache.set(self._CACHE_KEY_UA_TOKEN, None, 0)

        if self.matches["vod"]:
            log.debug("Found video URL: authentication is required.")
            self.auth()

        json_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//*[@data-video-json][1]/@data-video-json"),
            ),
        )
        if not json_url:
            return

        json_url = urlunparse(urlparse(self.url)._replace(path=json_url))
        log.debug(f"Found JSON URL: {json_url}")

        content_url = self.session.http.get(
            json_url,
            schema=validate.Schema(
                validate.parse_json(),
                {"video": {"content_url": validate.url()}},
                validate.get(("video", "content_url")),
            ),
        )
        if not content_url:
            log.error("Missing content URL")
            return

        content_url = content_url.replace("/relinkerServlet.mp4", "/relinkerServlet.htm")
        parsed = urlparse(content_url)
        params = dict(parse_qsl(parsed.query))
        if not parsed.path.endswith(".xml") and not params.get("output"):
            params["output"] = self._DEFAULT_MEDIAPOLIS_OUTPUT
            content_url = update_qsd(urlunparse(parsed), params)

        res = self.session.http.head(content_url)
        # status code will be 200 even if geo-blocked, so check the returned content-type
        if not res or not res.headers or res.headers["Content-Type"] == "video/mp4":
            log.error("Geo-restricted content")
            return

        stream_url = self.session.http.get(
            content_url,
            schema=validate.Schema(
                validate.parse_xml(),
                validate.xml_element(tag="Mediapolis"),
                validate.xml_xpath_string("./url[@type='content']/text()"),
                validate.none_or_all(
                    validate.transform(str.strip),
                    validate.url(path=validate.endswith(".m3u8")),
                ),
            ),
        )
        if not stream_url:
            log.error("Missing stream URL")
            return

        yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()

    def login(self):
        if not self.get_option("email") or not self.get_option("password"):
            raise PluginError("This RaiPlay content requires a login using --raiplay-email and --raiplay-password")

        login_error, ua_token, expiration = self.session.http.post(
            self._AUTH_URL,
            data={
                "email": self.get_option("email"),
                "password": self.get_option("password"),
                "domainApiKey": self._DOMAIN_API_KEY,
            },
            headers={
                "Referer": self.url,
                "Origin": self.url,
            },
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "response": "OK",
                            "ua": str,
                            "authorization": validate.all(
                                str,
                                validate.transform(str.split, "."),
                                validate.length(3, op="eq"),
                                validate.get(1),
                                validate.transform(lambda s: base64.b64decode(f"{s}{'=' * (-len(s) % 4)}")),
                                validate.parse_json(),
                                {"exp": int},
                                validate.get("exp"),
                                validate.transform(fromtimestamp),
                            ),
                        },
                        validate.union_get(None, "ua", "authorization"),
                    ),
                    validate.all(
                        {
                            "response": str,
                            "message": str,
                        },
                        validate.union_get("message", None, None),
                    ),
                ),
            ),
        )

        if login_error or not ua_token:
            raise PluginError(login_error or "Authentication failure")

        return ua_token, expiration

    def auth(self):
        if ua_token := self.cache.get(self._CACHE_KEY_UA_TOKEN):
            log.info("Using cached user-authentication token")
        else:
            ua_token, expiration = self.login()
            self.cache.set(self._CACHE_KEY_UA_TOKEN, ua_token, expires_at=expiration)

        self.session.http.headers.update({"x-ua-token": ua_token})


__plugin__ = RaiPlay
