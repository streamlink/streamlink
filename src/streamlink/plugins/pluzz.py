"""
$description Live TV channels and video on-demand service from france.tv, a French public, state-owned broadcaster.
$url france.tv
$url francetvinfo.fr
$type live, vod
$metadata title
$region France, Andorra, Monaco
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.times import localnow


log = logging.getLogger(__name__)


@pluginmatcher(
    name="francetv",
    pattern=re.compile(r"https?://(?:[\w-]+\.)?france\.tv/"),
)
@pluginmatcher(
    name="francetvinfofr",
    pattern=re.compile(r"https?://(?:[\w-]+\.)?francetvinfo\.fr/"),
)
class Pluzz(Plugin):
    PLAYER_VERSION = "5.51.35"

    _URL_GEO = "https://geoftv-a.akamaihd.net/ws/edgescape.json"
    _URL_API = "https://k7.ftven.fr/videos/{video_id}"

    _SCHEMA_VIDEOID_FRANCETV = validate.Schema(
        validate.regex(
            re.compile(r"""\\"options\\":\{\\"id\\":\\"(?P<video_id>[\dA-Fa-f-]{36})\\","""),
            method="search",
        ),
        validate.get("video_id"),
    )
    _SCHEMA_VIDEOID_FRANCETVINFOFR = validate.Schema(
        validate.parse_html(),
        validate.any(
            # overseas live stream
            validate.all(
                validate.xml_xpath_string(""".//script[contains(text(),'"data":{content:{player:{id:"')][1]/text()"""),
                str,
                validate.regex(
                    re.compile(r""""data":\{content:\{player:\{id:"(?P<video_id>[\dA-Fa-f-]{36})","""),
                    method="search",
                ),
                validate.get("video_id"),
            ),
            # news article
            validate.all(
                validate.xml_xpath_string(".//*[@id][contains(@class,'francetv-player-wrapper')][1]/@id"),
                str,
            ),
            # videos
            validate.all(
                validate.xml_xpath_string(".//*[@data-id][contains(@class,'magneto')][1]/@data-id"),
                str,
            ),
            validate.transform(lambda *_: None),
        ),
    )

    def _get_video_id(self):
        return self.session.http.get(
            self.url,
            schema=self._SCHEMA_VIDEOID_FRANCETV if self.matches["francetv"] else self._SCHEMA_VIDEOID_FRANCETVINFOFR,
        )

    def _get_streams(self):
        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
        })
        CHROME_VERSION = re.compile(r"Chrome/(\d+)").search(useragents.CHROME).group(1)

        if not (video_id := self._get_video_id()):
            return
        log.debug(f"Video ID: {video_id}")

        # Retrieve geolocation data
        country_code = self.session.http.get(
            self._URL_GEO,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "reponse": {
                        "geo_info": {
                            "country_code": str,
                        },
                    },
                },
                validate.get(("reponse", "geo_info", "country_code")),
            ),
        )
        log.debug(f"Country: {country_code}")

        video_format, token_url, url, self.title = self.session.http.get(
            self._URL_API.format(video_id=video_id),
            params={
                "country_code": country_code,
                "w": 1920,
                "h": 1080,
                "player_version": self.PLAYER_VERSION,
                "domain": urlparse(self.url).netloc,
                "device_type": "mobile",
                "browser": "chrome",
                "browser_version": CHROME_VERSION,
                "os": "ios",
                "gmt": localnow().strftime("%z"),
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "video": {
                        "format": validate.any("dash", "hls"),
                        "token": {
                            "akamai": validate.url(),
                        },
                        "url": validate.url(),
                    },
                    "meta": {
                        "title": str,
                    },
                },
                validate.union_get(
                    ("video", "format"),
                    ("video", "token", "akamai"),
                    ("video", "url"),
                    ("meta", "title"),
                ),
            ),
        )

        video_url = self.session.http.get(
            token_url,
            params={
                "url": url,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {"url": validate.url()},
                validate.get("url"),
            ),
        )

        if video_format == "dash":
            yield from DASHStream.parse_manifest(self.session, video_url).items()
        elif video_format == "hls":
            yield from HLSStream.parse_variant_playlist(self.session, video_url).items()


__plugin__ = Pluzz
