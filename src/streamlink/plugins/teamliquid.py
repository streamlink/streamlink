import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http


_url_re = re.compile(r'''https?://(?:www\.)?teamliquid\.net/video/streams/''')


class Teamliquid(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)

        stream_address_re = re.compile(r'''href\s*=\s*"([^"]+)"\s*>\s*View on''')

        stream_url_match = stream_address_re.search(res.text)
        if stream_url_match:
            stream_url = stream_url_match.group(1)
            self.logger.info("Attempting to play streams from {0}", stream_url)
            return self.session.streams(stream_url)


__plugin__ = Teamliquid
