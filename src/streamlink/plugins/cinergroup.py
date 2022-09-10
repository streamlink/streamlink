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
        showmax\.com\.tr/(canli-yayin|canliyayin)
        |
        showturk\.com\.tr/(canli-yayin|canliyayin)(/showtv)?
    )/?
""", re.VERBOSE))
class CinerGroup(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page = None

    @property
    def page(self):
        if self._page is None:
            self._page = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
            ))
        return self._page

    def _get_live_url(self):
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'videoUrl')]/text()"),
            validate.none_or_all(
                re.compile(r"""videoUrl\s*=\s*(?P<q>['"])(?P<url>.+?)(?P=q)"""),
                validate.none_or_all(
                    validate.get("url"),
                    validate.url(),
                ),
            ),
        )
        live_url = schema.validate(self.page) 
        return live_url
        
    def _get_live_url2(self):
        live_url = self.session.http.get(self.url, schema=validate.Schema(
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
        return live_url

    def _get_streams(self):
        live_url = self._get_live_url()
        if not live_url:
            live_url = self._get_live_url2()
        return HLSStream.parse_variant_playlist(self.session, live_url)


__plugin__ = CinerGroup
