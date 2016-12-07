import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

def html_unescape(s):
    parser = HTMLParser()
    return parser.unescape(s)

_url_re = re.compile(r"https?://(?:www\.)?vidio\.com/(?P<type>live|watch)/(?P<id>\d+)-(?P<name>[^/?#&]+)")
_clipdata_re = re.compile(r"""data-json-clips\s*=\s*(['"])(.*?)\1""")

_schema = validate.Schema(
    validate.transform(_clipdata_re.search),
    validate.any(
        None, 
        validate.all(
            validate.get(2),
            validate.transform(html_unescape),
            validate.transform(parse_json),
            [{
                "sources": [{
                    "file": validate.url(
                        scheme="http",
                        path=validate.endswith(".m3u8")
                    )
                }]
            }]
        )
    )
)

class Vidio(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        clips = http.get(self.url, schema=_schema)
        if not clips:
            return

        for clip in clips:
            for source in clip["sources"]:
                return HLSStream.parse_variant_playlist(self.session, source["file"])

__plugin__ = Vidio
