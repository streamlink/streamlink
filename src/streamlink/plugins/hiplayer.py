"""
$description United Arab Emirates CDN hosting live content for various websites in The Middle East.
$url alwasat.ly
$url media.gov.kw
$url rotana.net
$type live
$region various
"""

import base64
import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (
        alwasat\.ly
    |
        media\.gov\.kw
    |
        rotana\.net
    )
""", re.VERBOSE))
class HiPlayer(Plugin):
    DAI_URL = "https://pubads.g.doubleclick.net/ssai/event/{0}/streams"

    def _get_streams(self):
        js_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'https://hiplayer.hibridcdn.net/l/')]/text()"),
                validate.none_or_all(
                    re.compile(r"""(?P<q>['"])(?P<url>https://hiplayer.hibridcdn.net/l/.+?)(?P=q)"""),
                    validate.none_or_all(
                        validate.get("url"),
                        validate.url(),
                    ),
                ),
            ),
        )
        if not js_url:
            log.error("Could not find JS URL")
            return

        log.debug(f"JS URL={js_url}")

        data = self.session.http.get(
            js_url,
            schema=validate.Schema(
                re.compile(r"var \w+\s*=\s*\[(?P<data>.+)]\.join\([\"']{2}\)"),
                validate.none_or_all(
                    validate.get("data"),
                    validate.transform(lambda s: re.sub(r"['\", ]", "", s)),
                    validate.transform(lambda s: base64.b64decode(s)),
                    validate.parse_json(),
                    validate.any(
                        None,
                        {
                            "daiEnabled": bool,
                            "daiAssetKey": str,
                            "daiApiKey": str,
                            "streamUrl": validate.any(validate.url(), ""),
                        },
                    ),
                ),
            ),
        )
        if not data:
            log.error("Could not find base64 encoded JSON data")
            return

        hls_url = data["streamUrl"]

        if data["daiEnabled"]:
            log.debug("daiEnabled=true")
            hls_url = self.session.http.post(
                self.DAI_URL.format(data["daiAssetKey"]),
                data={"api-key": data["daiApiKey"]},
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "stream_manifest": validate.url(),
                    },
                    validate.get("stream_manifest"),
                ),
            )

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = HiPlayer
