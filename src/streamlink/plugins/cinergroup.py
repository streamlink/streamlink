"""
$description Turkish live TV channels from Ciner Group, including Haberturk TV and Show TV.
$url showtv.com.tr
$url haberturk.com
$url haberturk.tv
$url bloomberght.com
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
        bloomberght.com/tv
        |
        showmax\.com\.tr/canli-?yayin
        |
        showturk\.com\.tr/canli-?yayin(?:/showtv)?
    )/?
""", re.VERBOSE))
class CinerGroup(Plugin):
    def _get_live_url(self):
        return self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(), 'videoUrl')]/text()"),
            validate.none_or_all(
                re.compile(r"""videoUrl\s*=\s*(?P<q>['"])(?P<url>.+?)(?P=q)"""),
                validate.none_or_all(
                    validate.get("url"),
                    validate.url(),
                ),
            ),
        ))

        
    def _get_live_url2(self):
        return self.session.http.get(self.url, schema=validate.Schema(
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

    def _get_streams(self):
        live_url = self._get_live_url() or self._get_live_url2()
        if not live_url:
            return
        return HLSStream.parse_variant_playlist(self.session, live_url)


__plugin__ = CinerGroup
