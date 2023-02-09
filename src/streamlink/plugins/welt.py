"""
$description German news and documentaries TV channel, owned by Axel Springer SE.
$url welt.de
$type live, vod
$region Germany
"""

import re
from urllib.parse import quote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(\w+\.)?welt\.de/?",
))
class Welt(Plugin):
    _url_vod = "https://www.welt.de/onward/video/play/{0}"
    _schema = validate.Schema(
        validate.parse_html(),
        validate.xml_findtext(".//script[@type='application/json'][@data-content='VideoPlayer.Config']"),
        validate.parse_json(),
        validate.get("sources"),
        validate.filter(lambda obj: obj["extension"] == "m3u8"),
        validate.get((0, "src")),
    )

    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=self._schema)

        if "mediathek" in self.url.lower():
            url = self._url_vod.format(quote(hls_url, safe=""))
            hls_url = self.session.http.get(url, headers={"Referer": self.url}).url

        return HLSStream.parse_variant_playlist(self.session, hls_url, headers={"Referer": self.url})


__plugin__ = Welt
