"""
$description Bulgarian CDN hosting live content for various websites in Bulgaria.
$url armymedia.bg
$url bgonair.bg
$url bloombergtv.bg
$url bnt.bg
$url i.cdn.bg
$url nova.bg
$url mu-vi.tv
$type live
$region Bulgaria
"""

import re
from urllib.parse import urlparse

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


@pluginmatcher(
    name="armymedia",
    pattern=re.compile(r"https?://(?:www\.)?armymedia\.bg/?"),
)
@pluginmatcher(
    name="bgonair",
    pattern=re.compile(r"https?://(?:www\.)?bgonair\.bg/tvonline/?"),
)
@pluginmatcher(
    name="bloombergtv",
    pattern=re.compile(r"https?://(?:www\.)?bloombergtv\.bg/video/?"),
)
@pluginmatcher(
    name="bnt",
    pattern=re.compile(r"https?://(?:www\.)?(?:tv\.)?bnt\.bg/\w+(?:/\w+)?/?"),
)
@pluginmatcher(
    name="nova",
    pattern=re.compile(r"https?://(?:www\.)?nova\.bg/live/?"),
)
@pluginmatcher(
    name="mu-vi",
    pattern=re.compile(r"https?://(?:www\.)?mu-vi\.tv/LiveStreams/pages/Live\.aspx/?"),
)
@pluginmatcher(
    name="cdnbg",
    pattern=re.compile(r"https?://(?:www\.)?i\.cdn\.bg/live/?"),
)
class CDNBG(Plugin):
    @staticmethod
    def _find_url_regex(regex: re.Pattern) -> validate.all:
        return validate.all(
            validate.regex(regex),
            validate.get("url"),
        )

    @staticmethod
    def _find_url_xpath(xpath: str) -> validate.all:
        return validate.all(
            validate.xml_xpath_string(xpath),
            str,
        )

    def _get_streams(self):
        if "cdn.bg" in urlparse(self.url).netloc:
            player_url = self.url
            h = self.session.get_option("http-headers")
            if not h or not h.get("Referer"):
                log.error('Missing Referer for iframe URL, use --http-header "Referer=URL" ')
                return
            referer = h.get("Referer")
        else:
            referer = self.url
            player_url = self.session.http.get(
                self.url,
                schema=validate.Schema(
                    validate.any(
                        self._find_url_regex(
                            re.compile(r"'src',\s*'(?P<url>https?://i\.cdn\.bg/live/\w+)'\);"),
                        ),
                        validate.all(
                            validate.parse_html(),
                            validate.any(
                                self._find_url_xpath(".//iframe[contains(@src,'//i.cdn.bg/')][1]/@src"),
                                self._find_url_xpath(".//iframe[contains(@nitro-lazy-src,'//i.cdn.bg/')][1]/@nitro-lazy-src"),
                                self._find_url_xpath(".//source[contains(@src,'//i.cdn.bg/')][1]/@src"),
                                self._find_url_xpath(".//a[contains(@href,'//i.cdn.bg/')][1]/@href"),
                            ),
                        ),
                        # silently fail
                        validate.transform(lambda *_: None),
                    ),
                ),
            )

        if not player_url:
            log.error("Could not find player URL")
            return

        player_url = update_scheme("https://", player_url, force=False)
        log.debug(f"Found player URL: {player_url}")

        stream_url = self.session.http.get(
            player_url,
            headers={"Referer": referer},
            schema=validate.Schema(
                validate.any(
                    self._find_url_regex(
                        re.compile(r"sdata\.src.*?=.*?(?P<q>[\"'])(?P<url>.*?)(?P=q)"),
                    ),
                    self._find_url_regex(
                        re.compile(r"(src|file)\s*:\s*(?P<q>[\"'])(?P<url>(https?:)?//.+?m3u8.*?)(?P=q)"),
                    ),
                    validate.all(
                        validate.regex(re.compile(r"""window\.APP_CONFIG\.stream\s*=\s*(?P<url>".+?");""")),
                        validate.get("url"),
                        validate.parse_json(),
                    ),
                    validate.all(
                        validate.parse_html(),
                        validate.any(
                            self._find_url_xpath(".//video[contains(@src,'m3u8')][1]/@src"),
                            self._find_url_xpath(".//source[contains(@src,'m3u8')][1]/@src"),
                        ),
                    ),
                    # GEOBLOCKED
                    self._find_url_regex(
                        re.compile(r"(?P<url>[^\"]+geoblock[^\"]+)"),
                    ),
                ),
            ),
        )
        if "geoblock" in stream_url:
            log.error("Geo-restricted content")
            return

        stream_url = update_scheme(player_url, stream_url)

        return (
            HLSStream.parse_variant_playlist(self.session, stream_url, headers={"Referer": "https://i.cdn.bg/"})
            or {"live": HLSStream(self.session, stream_url, headers={"Referer": "https://i.cdn.bg/"})}
        )  # fmt: skip


__plugin__ = CDNBG
