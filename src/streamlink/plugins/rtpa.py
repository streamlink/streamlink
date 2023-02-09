"""
$description Live TV channels and video on-demand service from RTPA, a Spanish public broadcaster.
$url rtpa.es
$type live, vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"https?://(?:www\.)?rtpa\.es"))
class RTPA(Plugin):
    def _get_streams(self):
        hls_url, self.title = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.union((
                validate.xml_xpath_string(".//video/source[@src][@type='application/x-mpegURL'][1]/@src"),
                validate.xml_xpath_string(".//head/title[1]/text()"),
            )),
        ))
        if not hls_url:
            return
        return HLSStream.parse_variant_playlist(self.session, hls_url, headers={"Referer": self.url})


__plugin__ = RTPA
