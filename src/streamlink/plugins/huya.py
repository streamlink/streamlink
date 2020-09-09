import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.plugin.api import useragents
from streamlink.utils import update_scheme

HUYA_URL = "http://m.huya.com/%s"

_url_re = re.compile(r'https?://(www\.)?huya.com/(?P<channel>[^/]+)')
_hls_re = re.compile(r'liveLineUrl\s*=\s*"(?P<url>[^"]+)"')

_hls_schema = validate.Schema(
    validate.transform(_hls_re.search),
    validate.any(None, validate.get("url")),
    validate.transform(lambda v: update_scheme("http://", v)),
    validate.url()
)


class Huya(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        self.session.http.headers.update({"User-Agent": useragents.IPAD})
        # Some problem with SSL on huya.com now, do not use https

        hls_url = self.session.http.get(HUYA_URL % channel, schema=_hls_schema)
        yield "live", HLSStream(self.session, hls_url)


__plugin__ = Huya
