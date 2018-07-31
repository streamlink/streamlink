import logging
import re

from streamlink.compat import urlparse, parse_qsl
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Mjunoon(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?mjunoon\.tv/")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        res = self.session.http.get(self.url)
        for script in itertags(res.text, 'script'):
            if script.attributes.get("id") == "playerScript":
                log.debug("Found the playerScript script tag")
                urlparts = urlparse(script.attributes.get("src"))
                i = 0

                for key, url in parse_qsl(urlparts.query):
                    if key == "streamUrl":
                        i += 1
                        for s in HLSStream.parse_variant_playlist(self.session, url, params=dict(id=i), verify=False).items():
                            yield s


__plugin__ = Mjunoon
