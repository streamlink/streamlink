"""
$description United Arab Emirates CDN hosting live content for various websites in The Middle East.
$url cnbcarabia.com
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
        cnbcarabia\.com
    |
        media\.gov\.kw
    |
        rotana\.net
    )
""", re.VERBOSE))
class HiPlayer(Plugin):
    DAI_URL = "https://pubads.g.doubleclick.net/ssai/event/{0}/streams"
    js_url_re = re.compile(r"""['"](https://hiplayer.hibridcdn.net/l/[^'"]+)['"]""")
    base64_data_re = re.compile(r"i\s*=\s*\[(.*)\]\.join")

    def _get_streams(self):
        js_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'https://hiplayer.hibridcdn.net/l/')]/text()"),
                validate.any(
                    None,
                    validate.all(
                        validate.transform(self.js_url_re.search),
                        validate.any(None, validate.all(validate.get(1), validate.url())),
                    ),
                ),
            ),
        )

        if not js_url:
            return

        log.debug("JS URL={0}".format(js_url))

        data = self.session.http.get(
            js_url,
            schema=validate.Schema(
                validate.transform(self.base64_data_re.search),
                validate.any(
                    None,
                    validate.all(
                        validate.get(1),
                        validate.transform(lambda s: re.sub(r"['\", ]", "", s)),
                        validate.transform(lambda s: base64.b64decode(s)),
                        validate.parse_json(),
                        validate.any(
                            None,
                            {
                                "daiEnabled": bool,
                                "daiAssetKey": validate.text,
                                "daiApiKey": validate.text,
                                "streamUrl": validate.any(validate.url(), ""),
                            },
                        ),
                    ),
                ),
            ),
        )

        hls_url = data["streamUrl"]

        if data["daiEnabled"]:
            log.debug("daiEnabled=true")
            hls_url = self.session.http.post(
                self.DAI_URL.format(data['daiAssetKey']),
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
