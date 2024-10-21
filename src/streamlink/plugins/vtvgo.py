"""
$description Live TV channels from VTV, a Vietnamese public, state-owned broadcaster.
$url vtvgo.vn
$type live
$webbrowser Required for circumventing the AWS Web Application Firewall bot-detection.
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.webbrowser.aws_waf import AWSWAF
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://vtvgo\.vn/xem-truc-tuyen-kenh-"))
class VTVgo(Plugin):
    AJAX_URL = "https://vtvgo.vn/ajax-get-stream"

    def _get_streams(self):
        if (
            not self.session.http.cookies.get(AWSWAF.TOKEN)
            or not self.session.http.get(self.url).content
        ):  # fmt: skip
            log.info("Getting new AWS WAF token (bot-detection)")
            if not AWSWAF(self.session).acquire(self.url):
                return
            self.save_cookies()

        self.session.http.headers.update(
            {
                "Origin": "https://vtvgo.vn",
                "Referer": self.url,
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        params = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'setplayer(')][1]/text()"),
                validate.none_or_all(
                    validate.regex(
                        re.compile(r"""var\s+(?P<key>(?:type_)?id|time|token)\s*=\s*["']?(?P<value>[^"']+)["']?;"""),
                        method="findall",
                    ),
                    [
                        ("id", int),
                        ("type_id", str),
                        ("time", str),
                        ("token", str),
                    ],
                ),
            ),
        )
        if not params:
            return

        log.trace(f"{params!r}")
        hls_url = self.session.http.post(
            self.AJAX_URL,
            data=dict(params),
            schema=validate.Schema(
                validate.parse_json(),
                {"stream_url": [validate.url()]},
                validate.get(("stream_url", 0)),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = VTVgo
