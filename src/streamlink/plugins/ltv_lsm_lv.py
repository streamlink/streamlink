import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class LtvLsmLv(Plugin):
    """
    Support for Latvian live channels streams on ltv.lsm.lv
    """
    url_re = re.compile(r"https?://ltv\.lsm\.lv/lv/tieshraide")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({"Referer": self.url})

        iframe_url = None
        res = self.session.http.get(self.url)
        for iframe in itertags(res.text, "iframe"):
            if "embed.lsm.lv" in iframe.attributes.get("src"):
                iframe_url = iframe.attributes.get("src")
                break

        if not iframe_url:
            log.error("Could not find player iframe")
            return

        log.debug("Found iframe: {0}".format(iframe_url))
        res = self.session.http.get(iframe_url)
        for source in itertags(res.text, "source"):
            if source.attributes.get("src"):
                stream_url = source.attributes.get("src")
                url_path = urlparse(stream_url).path
                if url_path.endswith(".m3u8"):
                    yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()
                else:
                    log.debug("Not used URL path: {0}".format(url_path))


__plugin__ = LtvLsmLv
