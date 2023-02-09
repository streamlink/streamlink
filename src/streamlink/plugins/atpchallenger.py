"""
$description Tennis tournaments organized by the Association of Tennis Professionals.
$url atptour.com/en/atp-challenger-tour/challenger-tv
$type live, vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?atptour\.com/(?:en|es)/atp-challenger-tour/challenger-tv",
))
class AtpChallengerTour(Plugin):
    def _get_streams(self):
        iframe_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//iframe[starts-with(@id,'vimeoPlayer_')][@src][1]/@src"),
            validate.any(None, validate.url()),
        ))
        if iframe_url:
            return self.session.streams(iframe_url)


__plugin__ = AtpChallengerTour
