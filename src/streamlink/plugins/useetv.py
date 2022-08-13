"""
$description Live TV channels and video on-demand service from UseeTV, owned by Telkom Indonesia.
$url useetv.com
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?useetv\.com/"))
class UseeTV(Plugin):
    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(validate.parse_html()))

        for needle, errormsg in (
            (
                "\"This service is not available in your Country\"",
                "The content is not available in your region",
            ),
            (
                "\"Silahkan login Menggunakan akun MyIndihome dan berlangganan minipack\"",
                "The content is not available without a subscription",
            ),
        ):
            if validate.Schema(validate.xml_xpath(".//script[contains(text(),$needle)]", needle=needle)).validate(root):
                log.error(errormsg)
                return

        url = validate.Schema(
            validate.any(
                validate.all(
                    validate.xml_xpath_string("""
                        .//script[contains(text(), 'laylist.m3u8') or contains(text(), 'manifest.mpd')][1]/text()
                    """),
                    str,
                    re.compile(r"""(?P<q>['"])(?P<url>https://.*?/(?:[Pp]laylist\.m3u8|manifest\.mpd).+?)(?P=q)"""),
                    validate.none_or_all(validate.get("url"), validate.url()),
                ),
                validate.all(
                    validate.xml_xpath_string(".//video[@id='video-player']/source/@src"),
                    validate.any(None, validate.url()),
                ),
            )
        ).validate(root)

        if url and ".m3u8" in url:
            return HLSStream.parse_variant_playlist(self.session, url)
        elif url and ".mpd" in url:
            return DASHStream.parse_manifest(self.session, url)


__plugin__ = UseeTV
