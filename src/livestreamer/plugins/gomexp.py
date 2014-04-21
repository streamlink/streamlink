"""Plugin for GOMeXP live streams.

This plugin is using the same API as the mobile app.
"""

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream
from livestreamer.utils import parse_xml

import re

API_BASE = "http://gox.gomexp.com/cgi-bin"
API_URL_APP = API_BASE + "/app_api.cgi"
API_URL_LIVE = API_BASE + "/gox_live.cgi"


class GOMeXP(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match(r"http(s)?://(www\.)?gomexp.com", url)

    def _get_live_cubeid(self):
        res = http.get(API_URL_APP, params=dict(mode="get_live"))
        root = parse_xml(res.text.encode("utf8"))
        return root.findtext("./cube/cubeid")

    def _get_streams(self):
        cubeid = self._get_live_cubeid()
        if not cubeid:
            return

        res = http.get(API_URL_LIVE, params=dict(cubeid=cubeid))
        root = parse_xml(res.text.encode("utf8"))
        streams = {}

        for entry in root.findall("./ENTRY/*/[@reftype='live'][@href]"):
            url = entry.get("href")

            try:
                hls_streams = HLSStream.parse_variant_playlist(self.session,
                                                               url)
                streams.update(hls_streams)
            except IOError as err:
                self.logger.error("Failed to open playlist: {0}", err)

        return streams

__plugin__ = GOMeXP
