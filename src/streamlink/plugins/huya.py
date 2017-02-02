import re

from requests.adapters import HTTPAdapter

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.plugin.api import useragents

HUYA_URL = "http://m.huya.com/%s"

_url_re = re.compile(r'http(s)?://(www\.)?huya.com/(?P<channel>[^/]+)', re.VERBOSE)
_hls_re = re.compile(r'^\s*<source\s+src="(?P<url>[^"]+)"/>', re.MULTILINE)

_hls_schema = validate.Schema(
        validate.all(
            validate.transform(_hls_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get('url'),
                    validate.transform(str)
                    )
                )
            )
        )

class Huya(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        http.headers.update({"User-Agent": useragents.IPAD})
        #Some problem with SSL on huya.com now, do not use https

        hls_url = http.get(HUYA_URL % channel, schema=_hls_schema)
        yield "live", HLSStream(self.session, hls_url)

__plugin__ = Huya
