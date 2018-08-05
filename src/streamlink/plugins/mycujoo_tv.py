import logging
import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)

class MycujooTv(Plugin):
    """
    Support for live and archived transmission of the matches and channels on mycujoo.tv
    """
    url_re = re.compile(r'https?://mycujoo\.tv/video/')
    streams_re = re.compile(r'"filename"\:.*?"([^"]*?)"')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        stream_url = None
        url = None
        res = self.session.http.get(self.url)
        streams = self.streams_re.search(res.text)

        if streams:
            stream_url = streams.group(1).replace("\/", "/")
            url = urlparse(stream_url)

        if url and ".m3u8" in url.path:
            log.debug("Found stream URL: {0}".format(url.geturl()))
            for s in HLSStream.parse_variant_playlist(self.session, stream_url).items():
                yield s
        log.error("Could not find the stream URL")


__plugin__ = MycujooTv
