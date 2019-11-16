import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class LineLive(Plugin):
    _url_re = re.compile(r"""
        https?://live\.line\.me
        /channels/(?P<channel>\d+)
        /broadcast/(?P<broadcast>\d+)
    """, re.VERBOSE)

    _api_url = "https://live-api.line-apps.com/app/v3.2/channel/{0}/broadcast/{1}/player_status"

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

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

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
        match = self._url_re.match(self.url)
        channel = match.group("channel")
        broadcast = match.group("broadcast")
        res = self.session.http.get(self._api_url.format(channel, broadcast))
        json = self.session.http.json(res, schema=self._player_status_schema)
        if json["liveStatus"] == "LIVE":
            return self._get_live_streams(json)
        elif json["liveStatus"] == "FINISHED":
            return self._get_vod_streams(json)
        return


__plugin__ = LineLive
