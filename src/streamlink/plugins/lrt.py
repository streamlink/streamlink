import logging
import re
from functools import partial

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.compat import urlparse

log = logging.getLogger(__name__)


class LRT(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?lrt.lt/mediateka/.")
    _source_re = re.compile(r'sources\s*:\s*(\[{.*?}\]),', re.DOTALL | re.IGNORECASE)
    js_to_json = partial(re.compile(r'(?!<")(\w+)\s*:\s*(["\']|\d?\.?\d+,|true|false|\[|{)').sub, r'"\1":\2')


    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        page = http.get(self.url)
        m = self._source_re.search(page.text)
        if m:
            params = ""
            data = m.group(1)
            log.debug("Source data: {0}".format(data))
            if "location.hash.substring" in data:
                log.debug("Removing hash substring addition")
                data = re.sub(r"\s*\+\s*location.hash.substring\(\d+\)", "", data)
                params = urlparse(self.url).fragment
            data = self.js_to_json(data)
            for stream in parse_json(data):
                for s in HLSStream.parse_variant_playlist(self.session, stream['file'], params=params).items():
                    yield s
        else:
            log.debug("No match for sources regex")


__plugin__ = LRT
