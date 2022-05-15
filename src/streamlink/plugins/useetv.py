"""
$description Live TV channels and video on-demand service from UseeTV, owned by Telkom Indonesia.
$url useetv.com
$type live, vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"https?://(?:www\.)?useetv\.com/"))
class UseeTV(Plugin):
    def find_url(self):
        url_re = re.compile(r"""['"](https://.*?/(?:[Pp]laylist\.m3u8|manifest\.mpd)[^'"]+)['"]""")

        return self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.any(
                validate.all(
                    validate.xml_xpath_string("""
                        .//script[contains(text(), 'laylist.m3u8') or contains(text(), 'manifest.mpd')][1]/text()
                    """),
                    validate.text,
                    validate.transform(url_re.search),
                    validate.any(None, validate.all(validate.get(1), validate.url())),
                ),
                validate.all(
                    validate.xml_xpath_string(".//video[@id='video-player']/source/@src"),
                    validate.any(None, validate.url()),
                ),
            ),
        ))

    def _get_streams(self):
        url = self.find_url()

        if url and ".m3u8" in url:
            return HLSStream.parse_variant_playlist(self.session, url)
        elif url and ".mpd" in url:
            return DASHStream.parse_manifest(self.session, url)


__plugin__ = UseeTV
