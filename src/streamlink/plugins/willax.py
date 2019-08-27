import logging
import re

from streamlink.compat import html_unescape
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags

log = logging.getLogger(__name__)


class Willax(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?willax\.tv/en-vivo')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.FIREFOX})
        res = self.session.http.get(self.url)
        for iframe in itertags(res.text, 'iframe'):
            return self.session.streams(html_unescape(iframe.attributes.get('src')))


__plugin__ = Willax
