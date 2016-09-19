"""Plugin for GOMeXP live streams.

This plugin is using the same API as the mobile app.
"""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

API_BASE = "http://gox.gomexp.com/cgi-bin"
API_URL_APP = API_BASE + "/app_api.cgi"
API_URL_LIVE = API_BASE + "/gox_live.cgi"

_url_re = re.compile("http(s)?://(www\.)?gomexp.com")

_entries_schema = validate.Schema(
    validate.xml_findall("./ENTRY/*/[@reftype='live'][@href]"),
    [validate.get("href")]
)


class GOMeXP(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_live_cubeid(self):
        res = http.get(API_URL_APP, params=dict(mode="get_live"))
        root = http.xml(res)
        return root.findtext("./cube/cubeid")

    def _get_streams(self):
        cubeid = self._get_live_cubeid()
        if not cubeid:
            return

        res = http.get(API_URL_LIVE, params=dict(cubeid=cubeid))
        entries = http.xml(res, schema=_entries_schema)
        streams = {}
        for url in entries:
            try:
                streams.update(
                    HLSStream.parse_variant_playlist(self.session, url)
                )
            except IOError as err:
                self.logger.error("Failed to open playlist: {0}", err)

        return streams

__plugin__ = GOMeXP
