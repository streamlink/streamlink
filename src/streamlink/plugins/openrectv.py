import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

_url_re = re.compile(r"https?://(?:www\.)?openrec.tv/(live|movie)/")
_playlist_url_re = re.compile(r"data-(source)?file=\"(?P<url>[^\"]+)\"")
_movie_data_re = re.compile(r'''<script type="application/ld\+json">(.*?)</script>''', re.DOTALL | re.M)
_live_schema = validate.Schema(
    validate.transform(_playlist_url_re.findall),
    [
        validate.union({
            "isSource": validate.all(validate.get(0), validate.transform(lambda s: s == "source")),
            "url": validate.all(validate.get(1), validate.url(scheme="http",
                                                              path=validate.endswith(".m3u8")))
        })
    ]
)
_movie_schema = validate.Schema(
    validate.transform(_movie_data_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.transform(parse_json),
            validate.get("contentUrl")
        )
    )
)


class OPENRECtv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return 1080 + 1, "openrectv"
        return Plugin.stream_weight(stream)

    def _get_streams(self):
        stype = _url_re.match(self.url).group(1)
        if stype.lower() == "live":
            self.logger.debug("Searching the page for live stream URLs")
            playlists = http.get(self.url, schema=_live_schema)
            for playlist in playlists:
                for q, s in HLSStream.parse_variant_playlist(self.session, playlist["url"]).items():
                    yield "source" if playlist["isSource"] else q, s
        elif stype.lower() == "movie":
            self.logger.debug("Searching the page for VOD stream URLs")
            playlist = http.get(self.url, schema=_movie_schema)
            if playlist:
                for s in HLSStream.parse_variant_playlist(self.session, playlist).items():
                    yield s


__plugin__ = OPENRECtv
