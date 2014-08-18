import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream

USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 "
    "(KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25"
)
HEADERS = {"User-Agent": USER_AGENT}
PLAYLIST_URL = "http://m.afreeca.com/live/stream/a/hls/broad_no/{broad_no}"
BROAD_INFO_URL = "https://api.m.afreeca.com/broad/a/getbroadinfo"

_broadcast_re = re.compile(r".+\/(\d+)\.gif")
_url_re = re.compile("http(s)?://(\w+\.)?afreeca.com/(?P<username>\w+)")

_broadcast_schema = validate.Schema(
    {
        "data": validate.any(
            None,
            {
                "broad_no": int,
            }
        )
    },
    validate.get("data")
)


class AfreecaTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_broadcast(self, username):
        data = {
            "szBjId": username
        }
        res = http.post(BROAD_INFO_URL, headers=HEADERS, data=data)

        return http.json(res, schema=_broadcast_schema)

    def _get_streams(self):
        match = _url_re.match(self.url)
        username = match.group("username")

        broadcast = self._get_broadcast(username)
        if not broadcast:
            return

        playlist_url = PLAYLIST_URL.format(**broadcast)
        stream = HLSStream(self.session, playlist_url, headers=HEADERS)

        return dict(live=stream)


__plugin__ = AfreecaTV
