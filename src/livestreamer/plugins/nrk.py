import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream

COOKIE_PARAMS = (
    "devicetype=desktop&"
    "preferred-player-odm=hlslink&"
    "preferred-player-live=hlslink"
)

_url_re = re.compile("http://(tv|radio).nrk.no/")
_media_url_re = re.compile("""
    <div[^>]*?id="playerelement"[^>]+
    data-media="(?P<url>[^"]+)"
""", re.VERBOSE)

_schema = validate.Schema(
    validate.transform(_media_url_re.search),
    validate.any(
        None,
        validate.all(
            validate.get("url"),
            validate.url(
                scheme="http",
                path=validate.endswith(".m3u8")
            )
        )
    )
)


class NRK(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        stream_type = _url_re.match(self.url).group(1).upper()
        cookie = {
            "NRK_PLAYER_SETTINGS_{0}".format(stream_type): COOKIE_PARAMS
        }
        playlist_url = http.get(self.url, cookies=cookie, schema=_schema)
        if not playlist_url:
            return

        return HLSStream.parse_variant_playlist(self.session, playlist_url)

__plugin__ = NRK
