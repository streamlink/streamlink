import logging
import re
from functools import partial

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.compat import urlparse

log = logging.getLogger(__name__)


class LRT(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?lrt.lt/mediateka/.")
    _source_re = re.compile(r'sources\s*:\s*(\[{.*?}\]),', re.DOTALL | re.IGNORECASE)


    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        page = self.session.http.get(self.url)
        m = self._source_re.search(page.text)
        if m:
            params = ""
            log.debug("AJAX call to: {0}".format(m.group(1)))
            ajaxpage = self.session.http.get(m.group(1))
            data = ajaxpage.text
            log.debug("AJAX response: {0}".format(data))
            ajaxObj = parse_json(data)
            m3u8_url = ajaxObj["response"]["data"]["content"]
            if m3u8_url:
                for s in HLSStream.parse_variant_playlist(self.session, m3u8_url, params=params).items():
                    yield s
        else:
            log.debug("No match for sources regex")


__plugin__ = LRT
