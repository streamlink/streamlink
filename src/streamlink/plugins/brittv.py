import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.compat import urljoin
from streamlink.stream import HLSStream


class BritTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?brittv\.co.uk/watch/")
    js_re = re.compile(r"""/js/brittv\.player\.js\.php\?key=([^'"]+)['"]""")
    player_re = re.compile(r"file: '(http://[^']+)'")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url, headers={"User-Agent": useragents.CHROME})
        m = self.js_re.search(res.text)
        if m:
            self.logger.debug("Found js key: {0}", m.group(1))
            js_url = m.group(0)
            res = http.get(urljoin(self.url, js_url))

            for url in self.player_re.findall(res.text):
                if "adblock" not in url:
                    yield "live", HLSStream(self.session, url)

__plugin__ = BritTV
