import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream

_url_re = re.compile(r"https://www.arconaitv.me/([^/]+)/")

SOURCES_RE = re.compile(r" data-item='([^']+)' ")
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36"

class ArconaiTv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        page = http.get(self.url)
        match = SOURCES_RE.search(page.text)
        if match is None:
            return

        sources = parse_json(match.group(1))
        if "sources" not in sources or not isinstance(sources["sources"], list):
            return

        for source in sources["sources"]:
            if "src" not in source or not source["src"].endswith(".m3u8"):
                continue

            yield "live", HLSStream(self.session, source["src"], headers={"User-Agent": USER_AGENT})

__plugin__ = ArconaiTv
