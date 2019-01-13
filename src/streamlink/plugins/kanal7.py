import logging
import re

from streamlink.compat import urljoin, urlparse
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class Kanal7(Plugin):
    url_re = re.compile(r"https?://(?:www.)?(?:kanal7\.com|tvt\.tv\.tr)/canli-(?:izle|yayin)")
    iframe_re = re.compile(r'iframe .*?src="([^"]*?iframe\.php)"')
    stream_re = re.compile(r'''video-source(?:\s*=\s*|["'],)['"](http[^"']*?)['"]''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def find_iframe(self, url):
        res = self.session.http.get(url)
        # find iframe url
        iframe = self.iframe_re.search(res.text)
        iframe_url = iframe and iframe.group(1)
        if iframe_url:
            parsed = urlparse(iframe_url)
            if not parsed.netloc:
                iframe_url = urljoin(self.url, iframe_url)
            iframe_url = update_scheme(self.url, iframe_url)
            log.debug("Found iframe: {0}".format(iframe_url))
        return iframe_url

    def _get_streams(self):
        iframe1 = self.find_iframe(self.url)
        if iframe1:
            ires = self.session.http.get(iframe1)
            stream_m = self.stream_re.search(ires.text)
            stream_url = stream_m and stream_m.group(1)
            if stream_url:
                yield "live", HLSStream(self.session, stream_url, headers={"Referer": iframe1})
        else:
            log.error("Could not find iframe, has the page layout changed?")


__plugin__ = Kanal7
