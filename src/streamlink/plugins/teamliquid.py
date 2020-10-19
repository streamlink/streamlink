import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin
from streamlink.plugins.afreeca import AfreecaTV
from streamlink.plugins.twitch import Twitch

log = logging.getLogger(__name__)


class Teamliquid(Plugin):
    _url_re = re.compile(r'''https?://(?:www\.)?(?:tl|teamliquid)\.net/video/streams/''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)

        stream_address_re = re.compile(r'''href\s*=\s*"([^"]+)"\s*>\s*View on''')

        stream_url_match = stream_address_re.search(res.text)
        if stream_url_match:
            stream_url = stream_url_match.group(1)
            log.info("Attempting to play streams from {0}".format(stream_url))
            p = urlparse(stream_url)
            if p.netloc.endswith("afreecatv.com"):
                self.stream_weight = AfreecaTV.stream_weight
            elif p.netloc.endswith("twitch.tv"):
                self.stream_weight = Twitch.stream_weight
            return self.session.streams(stream_url)


__plugin__ = Teamliquid
