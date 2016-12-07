import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream, HTTPStream

_url_re = re.compile("http(s)?://(\w+\.)?seemeplay.ru/")
_player_re = re.compile("""
    SMP.(channel|video).player.init\({
    \s+file:\s+"([^"]+)"
""", re.VERBOSE)

_schema = validate.Schema(
    validate.transform(_player_re.search),
    validate.any(
        None,
        validate.union({
            "type": validate.get(1),
            "url": validate.all(
                validate.get(2),
                validate.url(scheme="http"),
            ),
        })
    )
)


class SeeMePlay(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, schema=_schema)
        if not res:
            return

        if res["type"] == "channel" and urlparse(res["url"]).path.endswith("m3u8"):
            return HLSStream.parse_variant_playlist(self.session, res["url"])
        elif res["type"] == "video":
            stream = HTTPStream(self.session, res["url"])
            return dict(video=stream)

__plugin__ = SeeMePlay
