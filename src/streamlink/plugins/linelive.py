"""
$description Japanese live streaming and video hosting social platform.
$url live.line.me
$type live, vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://live\.line\.me/channels/(?P<channel>\d+)/broadcast/(?P<broadcast>\d+)"
))
class LineLive(Plugin):
    _api_url = "https://live-api.line-apps.com/web/v4.0/channel/{0}/broadcast/{1}/player_status"

    _player_status_schema = validate.Schema(
        {
            "liveStatus": validate.text,
            "liveHLSURLs": validate.any(None, {
                "720": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "480": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "360": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "240": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "144": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            }),
            "archivedHLSURLs": validate.any(None, {
                "720": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "480": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "360": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "240": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                "144": validate.any(None, validate.url(scheme="http", path=validate.endswith(".m3u8"))),
            }),
        })

    def _get_live_streams(self, json):
        for stream in json["liveHLSURLs"]:
            url = json["liveHLSURLs"][stream]
            if url is not None:
                yield "{0}p.".format(stream), HLSStream(self.session, url)

    def _get_vod_streams(self, json):
        for stream in json["archivedHLSURLs"]:
            url = json["archivedHLSURLs"][stream]
            if url is not None:
                yield "{0}p.".format(stream), HLSStream(self.session, url)

    def _get_streams(self):
        channel = self.match.group("channel")
        broadcast = self.match.group("broadcast")
        res = self.session.http.get(self._api_url.format(channel, broadcast))
        json = self.session.http.json(res, schema=self._player_status_schema)
        if json["liveStatus"] == "LIVE":
            return self._get_live_streams(json)
        elif json["liveStatus"] == "FINISHED":
            return self._get_vod_streams(json)
        return


__plugin__ = LineLive
