import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.compat import urlparse
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)

class KardelenTV(Plugin):
    url_re = re.compile(r'http?://(?:www\.)?kardelentv\.com\.tr/kardelen-tv-canli-izle')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_title(self):
        return "Kardelen TV"

    def _get_streams(self):
        res = self.session.http.get(self.url)
        for iframe in itertags(res.text, "iframe"):
            self.logger.debug("Found iframe: {0}".format(iframe))
            iframe_res = self.session.http.get(iframe.attributes['src'], headers={"Referer": self.url})
            for source in itertags(iframe_res.text, "source"):
                if source.attributes.get("src"):
                    stream_url = source.attributes.get("src")
                    url_path = urlparse(stream_url).path
                    if url_path.endswith(".m3u8"):
                        for s in HLSStream.parse_variant_playlist(self.session,
                                                                stream_url).items():
                            yield s
                    else:
                        log.debug("Not used URL path: {0}".format(url_path))

__plugin__ = KardelenTV
