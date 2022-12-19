"""
$description Bulgarian CDN hosting live content for various websites in Bulgaria.
$url armymedia.bg
$url bgonair.bg
$url bloombergtv.bg
$url bnt.bg
$url live.bstv.bg
$url i.cdn.bg
$url nova.bg
$url mu-vi.tv
$type live
$region Bulgaria
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?(?:
        armymedia\.bg
        |
        bgonair\.bg/tvonline
        |
        bloombergtv\.bg/video
        |
        (?:tv\.)?bnt\.bg/\w+(?:/\w+)?
        |
        live\.bstv\.bg
        |
        i\.cdn\.bg/live/
        |
        nova\.bg/live
        |
        mu-vi\.tv/LiveStreams/pages/Live\.aspx
    )/?
""", re.VERBOSE))
class CDNBG(Plugin):
    @staticmethod
    def _find_url(regex: re.Pattern) -> validate.all:
        return validate.all(
            validate.regex(regex),
            validate.get("url"),
        )

    def _get_streams(self):
        if "cdn.bg" in urlparse(self.url).netloc:
            iframe_url = self.url
            h = self.session.get_option("http-headers")
            if not h or not h.get("Referer"):
                log.error("Missing Referer for iframe URL, use --http-header \"Referer=URL\" ")
                return
            _referer = h.get("Referer")
        else:
            _referer = self.url
            iframe_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.any(
                    self._find_url(
                        re.compile(r"'src',\s*'(?P<url>https?://i\.cdn\.bg/live/\w+)'\);")
                    ),
                    validate.all(
                        validate.parse_html(),
                        validate.xml_xpath_string(".//iframe[contains(@src,'cdn.bg')][1]/@src")
                    )
                )
            ))

        if not iframe_url:
            return

        iframe_url = update_scheme("https://", iframe_url, force=False)
        log.debug(f"Found iframe: {iframe_url}")

        stream_url = self.session.http.get(
            iframe_url,
            headers={"Referer": _referer},
            schema=validate.Schema(
                validate.any(
                    self._find_url(
                        re.compile(r"sdata\.src.*?=.*?(?P<q>[\"'])(?P<url>.*?)(?P=q)")
                    ),
                    self._find_url(
                        re.compile(r"(src|file): (?P<q>[\"'])(?P<url>(https?:)?//.+?m3u8.*?)(?P=q)")
                    ),
                    self._find_url(
                        re.compile(r"video src=(?P<url>http[^ ]+m3u8[^ ]*)")
                    ),
                    self._find_url(
                        re.compile(r"source src=\"(?P<url>[^\"]+m3u8[^\"]*)\"")
                    ),
                    # GEOBLOCKED
                    self._find_url(
                        re.compile(r"(?P<url>[^\"]+geoblock[^\"]+)")
                    ),
                )
            )
        )
        if "geoblock" in stream_url:
            log.error("Geo-restricted content")
            return

        return HLSStream.parse_variant_playlist(
            self.session,
            update_scheme(iframe_url, stream_url),
            headers={"Referer": "https://i.cdn.bg/"},
        )


__plugin__ = CDNBG
