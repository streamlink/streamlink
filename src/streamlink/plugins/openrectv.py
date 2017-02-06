import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

_url_re = re.compile(r"http(s)?://(www\.)?openrec.tv/(live|movie)/[^/?&]+")
_playlist_url_re = re.compile(r"data-(source)?file=\"(?P<url>[^\"]+)\"")
_schema = validate.Schema(
    validate.transform(_playlist_url_re.findall),
    [
        validate.union({
            "isSource": validate.all(validate.get(0), validate.transform(lambda s: s == "source")),
            "url": validate.all(validate.get(1), validate.url(scheme="http",
                                                       path=validate.endswith(".m3u8")))
        })
    ]
)


class OPENRECtv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return 1080 + 1, "openrectv"
        return Plugin.stream_weight(stream)

    def _get_streams(self):
        playlists = http.get(self.url, schema=_schema)
        for playlist in playlists:
            for q, s in HLSStream.parse_variant_playlist(self.session, playlist["url"]).items():
                yield "source" if playlist["isSource"] else q, s


__plugin__ = OPENRECtv
