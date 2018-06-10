import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.compat import urljoin
from streamlink.stream import HLSStream


class BritTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?brittv\.co.uk/watch/")
    js_re = re.compile(r"""/js/brittv\.player\.js\.php\?key=([^'"]+)['"]""")
    player_re = re.compile(r'''src\s*:\s*(?P<quote>['"])(https?://.+?)(?P=quote)''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @Plugin.broken()
    def _get_streams(self):
        http.headers.update({"User-Agent": useragents.CHROME})
        res = http.get(self.url)
        m = self.js_re.search(res.text)
        if m:
            self.logger.debug("Found js key: {0}", m.group(1))
            js_url = m.group(0)
            res = http.get(urljoin(self.url, js_url), headers={"Referer": self.url})

            self.logger.debug("Looking for stream URL...")
            for _, url in self.player_re.findall(res.text):
                if "adblock" not in url:
                    yield "live", HLSStream(self.session, url)


__plugin__ = BritTV
