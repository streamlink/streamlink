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

from streamlink.plugin import Plugin, PluginError, pluginmatcher
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
    GEO_URL = "https://geoftv-a.akamaihd.net/ws/edgescape.json"
    API_URL = "https://k7.ftven.fr/videos/{video_id}"

    def _get_streams(self):
        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
        })
        CHROME_VERSION = re.compile(r"Chrome/(\d+)").search(useragents.CHROME).group(1)

        # Retrieve geolocation data
        country_code = self.session.http.get(
            self.GEO_URL,
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

        # Retrieve URL page and search for video ID
        video_id = None
        try:
            video_id = self.session.http.get(
                self.url,
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.any(
                        # default francetv player
                        validate.all(
                            validate.xml_xpath_string(".//script[contains(text(),'window.FTVPlayerVideos')][1]/text()"),
                            str,
                            validate.regex(
                                re.compile(
                                    r"window\.FTVPlayerVideos\s*=\s*(?P<json>\[{.+?}])\s*;\s*(?:$|var)",
                                    re.DOTALL,
                                ),
                            ),
                            validate.get("json"),
                            validate.parse_json(),
                            [{"videoId": str}],
                            validate.get((0, "videoId")),
                        ),
                        # francetvinfo.fr overseas live stream
                        validate.all(
                            validate.xml_xpath_string(".//script[contains(text(),'magneto:{videoId:')][1]/text()"),
                            str,
                            validate.regex(re.compile(r"""magneto:\{videoId:(?P<q>['"])(?P<video_id>.+?)(?P=q)""")),
                            validate.get("video_id"),
                        ),
                        # francetvinfo.fr news article
                        validate.all(
                            validate.xml_xpath_string(".//*[@id][contains(@class,'francetv-player-wrapper')][1]/@id"),
                            str,
                        ),
                        # francetvinfo.fr videos
                        validate.all(
                            validate.xml_xpath_string(".//*[@data-id][contains(@class,'magneto')][1]/@data-id"),
                            str,
                        ),
                    ),
                ),
            )
        except PluginError:
            pass
        if not video_id:
            return
        log.debug(f"Video ID: {video_id}")

        video_format, token_url, url, self.title = self.session.http.get(
            self.API_URL.format(video_id=video_id),
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
