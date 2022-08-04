"""
$description Turkish live TV channels from Ciner Group, including Haberturk TV and Show TV.
$url showtv.com.tr
$url haberturk.com
$url haberturk.tv
$url showmax.com.tr
$url showturk.com.tr
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        showtv\.com\.tr/canli-yayin(/showtv)?
        |
        haberturk\.(?:com|tv)(?:/tv)?/canliyayin
        |
        showmax\.com\.tr/canliyayin
        |
        showturk\.com\.tr/canli-yayin/showturk
    )/?
""", re.VERBOSE))
class CinerGroup(Plugin):
    def _get_streams(self):
        stream_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//div[@data-ht][1]/@data-ht"),
            validate.none_or_all(
                validate.parse_json(),
                {
                    "ht_stream_m3u8": validate.url(),
                },
                validate.get("ht_stream_m3u8"),
            ),
        ))
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = CinerGroup
