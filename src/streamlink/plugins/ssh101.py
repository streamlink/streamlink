import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?ssh101\.com/")

_live_re = re.compile("""
\s*jwplayer\(\"player\"\)\.setup\({.*?
\s*primary:\s+"([^"]+)".*?
\s*file:\s+"([^"]+)"
""", re.DOTALL)

_live_schema = validate.Schema(
    validate.transform(_live_re.search),
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

class SSH101(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, schema=_live_schema)
        if not res:
            return

        if res["type"] == "hls" and urlparse(res["url"]).path.endswith("m3u8"):
            stream = HLSStream(self.session, res["url"])
            return dict(hls=stream)

__plugin__ = SSH101
