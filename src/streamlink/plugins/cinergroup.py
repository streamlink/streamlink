"""
$description Turkish live TV channels from Ciner Group, including Haberturk TV and Show TV.
$url bloomberght.com
$url haberturk.com
$url haberturk.tv
$url showmax.com.tr
$url showturk.com.tr
$url showtv.com.tr
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    name="bloomberght",
    pattern=re.compile(r"https?://(?:www\.)?bloomberght\.com/tv/?"),
)
@pluginmatcher(
    name="haberturk",
    pattern=re.compile(r"https?://(?:www\.)?haberturk\.(?:com|tv)(?:/tv)?/canliyayin/?"),
)
@pluginmatcher(
    name="showmax",
    pattern=re.compile(r"https?://(?:www\.)?showmax\.com\.tr/canli-?yayin/?"),
)
@pluginmatcher(
    name="showturk",
    pattern=re.compile(r"https?://(?:www\.)?showturk\.com\.tr/canli-?yayin(?:/showtv)?/?"),
)
@pluginmatcher(
    name="showtv",
    pattern=re.compile(r"https?://(?:www\.)?showtv\.com\.tr/canli-yayin(?:/showtv)?/?"),
)
class CinerGroup(Plugin):
    @staticmethod
    def _schema_videourl():
        return validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'videoUrl')]/text()"),
            validate.none_or_all(
                re.compile(r"""(?<!//)\s*var\s+videoUrl\s*=\s*(?P<q>['"])(?P<url>.+?)(?P=q)"""),
                validate.none_or_all(
                    validate.get("url"),
                    validate.url(),
                ),
            ),
        )

    @staticmethod
    def _schema_data_ht():
        return validate.Schema(
            validate.xml_xpath_string(".//div[@data-ht][1]/@data-ht"),
            validate.none_or_all(
                validate.parse_json(),
                {
                    "ht_stream_m3u8": validate.url(),
                },
                validate.get("ht_stream_m3u8"),
            ),
        )

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(validate.parse_html()))
        schema_getters = self._schema_videourl, self._schema_data_ht
        stream_url = next((res for res in (getter().validate(root) for getter in schema_getters) if res), None)

        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = CinerGroup
