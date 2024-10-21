"""
$description Live and on-demand streaming platform run by NASA
$url plus.nasa.gov
$type live, vod
$metadata title
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://plus\.nasa\.gov/"),
)
class NASAPlus(Plugin):
    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath(".//video[@id='main-video'][1]"),
                validate.none_or_all(
                    validate.get(0),
                    validate.union((
                        validate.xml_xpath_string("./source[@src][@type='application/x-mpegURL'][1]/@src"),
                        validate.get("title"),
                    )),
                ),
            ),
        )
        if not data:
            return None

        hls_url, self.title = data

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = NASAPlus
