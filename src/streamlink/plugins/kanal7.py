from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class Kanal7(Plugin):
    url_re = re.compile(r"https?://(?:www.)?kanal7.com/canli-izle")
    iframe_re = re.compile(r'iframe .*?src="(http://[^"]*?)"')
    stream_re = re.compile(r'source .*?src=*"(http[^"]*?)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        # find iframe url
        # open iframe page and extract m3u8 url
        iframe = self.iframe_re.search(res.text)
        iframe_url = iframe and iframe.group(1)
        if iframe_url:
            self.logger.debug("Found iframe: {}", iframe_url)
            ires = http.get(iframe_url)
            stream_m = self.stream_re.search(ires.text)
            stream_url = stream_m and stream_m.group(1)
            if stream_url:
                yield "live", HLSStream(self.session, stream_url)
        else:
            self.logger.error("Could not find iframe, has the page layout changed?")


__plugin__ = Kanal7
