"""
$description Video content from Telefe, an Argentine TV station.
$url mitelefe.com
$type live
$metadata title
$region Argentina
"""

import re
from urllib.parse import urlparse

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = getLogger(__name__)


@pluginmatcher(re.compile(r"https://mitelefe\.com/(?:telefe-en-)?vivo"))
class Telefe(Plugin):
    _URL_TOKENIZE = "https://mitelefe.com/vidya/tokenize"

    def _get_streams(self):
        self.title, stream_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.union((
                    validate.xml_xpath_string(".//meta[@property='og:title'][@content][1]/@content"),
                    validate.all(
                        validate.xml_xpath_string(".//*[@data-player-url][1]/@data-player-url"),
                        validate.none_or_all(
                            validate.url(),
                        ),
                    ),
                )),
            ),
        )
        if not stream_url:
            log.error("Could not find stream URL")
            return None

        parsed = urlparse(stream_url)
        netloc = parsed.netloc.removeprefix("www.")
        if netloc in ("youtube.com", "youtu.be", "dailymotion.com"):
            return self.session.streams(stream_url)

        headers = {
            "Origin": "https://mitelefe.com",
            "Referer": self.url,
        }

        hls_url = self.session.http.post(
            self._URL_TOKENIZE,
            headers={
                "Content-Type": "application/json",
                **headers,
            },
            json={
                "url": stream_url,
            },
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "url": validate.url(path=validate.endswith(".m3u8")),
                        },
                        validate.get("url"),
                    ),
                    validate.all(
                        str,
                        validate.url(path=validate.endswith(".m3u8")),
                    ),
                ),
            ),
        )
        if self.session.http.head(hls_url, raise_for_status=False).status_code >= 400:
            log.error("Access restricted")
            return None

        return HLSStream.parse_variant_playlist(self.session, hls_url, headers=headers)


__plugin__ = Telefe
