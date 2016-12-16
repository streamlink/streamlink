from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class Kanal7(Plugin):
    url_re = re.compile(r"https?://(?:www.)?kanal7.com/canli-izle")
    data_re = re.compile(r'''videoPlayer.setup\(\{\s*file:\s*"(http[^"]*?)"''', re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        data_m = self.data_re.search(res.text)
        if data_m:
            stream_url = data_m.group(1)
            self.logger.debug("Found stream: {}", stream_url)
            yield "live", HLSStream(self.session, stream_url)


__plugin__ = Kanal7
