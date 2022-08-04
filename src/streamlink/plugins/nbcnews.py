"""
$description 24-hour world, US and local news channel, based in the United States of America.
$url nbcnews.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?nbcnews\.com/now"
))
class NBCNews(Plugin):
    URL_API = "https://api-leap.nbcsports.com/feeds/assets/{}?application=NBCNews&format=nbc-player&platform=desktop"
    URL_TOKEN = "https://tokens.playmakerservices.com/"

    title = "NBC News Now"

    def _get_streams(self):
        self.id = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[@type='application/ld+json'][1]/text()"),
                validate.none_or_all(
                    validate.parse_json(),
                    {"embedUrl": validate.url()},
                    validate.get("embedUrl"),
                    validate.transform(lambda embed_url: embed_url.split("/")[-1]),
                ),
            ),
        )
        if self.id is None:
            return
        log.debug(f"API ID: {self.id}")

        stream = self.session.http.get(
            self.URL_API.format(self.id),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "videoSources": [{
                        "cdnSources": {
                            "primary": [{
                                "sourceUrl": validate.url(path=validate.endswith(".m3u8")),
                            }],
                        },
                    }],
                },
                validate.get(("videoSources", 0, "cdnSources", "primary", 0, "sourceUrl")),
            ),
        )

        url = self.session.http.post(
            self.URL_TOKEN,
            json={
                "requestorId": "nbcnews",
                "pid": self.id,
                "application": "NBCSports",
                "version": "v1",
                "platform": "desktop",
                "token": "",
                "resourceId": "",
                "inPath": "false",
                "authenticationType": "unauth",
                "cdn": "akamai",
                "url": stream,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "akamai": [{
                        "tokenizedUrl": validate.url(),
                    }],
                },
                validate.get(("akamai", 0, "tokenizedUrl")),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = NBCNews
