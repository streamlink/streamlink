import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

_url_re = re.compile("http(s)?://(\w+.)?chaturbate.com/[^/?&]+")
_playlist_url_re = re.compile("html \+= \"src='(?P<url>[^']+)'\";")
_schema = validate.Schema(
    validate.transform(_playlist_url_re.search),
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


class Chaturbate(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        playlist_url = http.get(self.url, schema=_schema)
        if not playlist_url:
            return

        return HLSStream.parse_variant_playlist(self.session, playlist_url)

__plugin__ = Chaturbate
