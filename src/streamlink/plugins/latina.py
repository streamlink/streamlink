"""
Support for the live stream on peruvian television site Latina (former called Frecuencia Latina)
    - http://www.latina.pe/tvenvivo
"""
import logging
import re
import time

from streamlink import PluginError
from streamlink.compat import quote, urlencode
from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.plugin.api import useragents
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)

class Latina(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?(latina.pe)/tvenvivo")
	
	# a valid url looks like this: 
	# http://live-normal-otros-hls.latina.pe/egress/bhandler/cialatina/live/manifest.m3u8?nva=1587935042&ttl=432000&ip=5.62.58.162&hash=03e2afa6c09712f3be919

    def __init__(self, url):
        super(Latina, self).__init__(url)
        self._page = None
        self.session.http.headers.update({
            "User-Agent": useragents.CHROME,
            "Referer": self.url,
		    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"})
	
		
    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def page(self):
        if not self._page:
            self._page = self.session.http.get(self.url)
        return self._page

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        self.session.http.get(self.url)
        stream_url = None
        for div in itertags(self.page.text, "div"):
            if div.attributes.get("id") == "player":
                stream_url = div.attributes.get("data-stream")

        if stream_url:
            #stream_url = "{0}?{1}".format(playlist_url, urlencode({"iut": token}))
            log.debug("stream_url {0}".format(stream_url))
            return HLSStream.parse_variant_playlist(self.session, stream_url)
        else:
            log.error("Could not find the live channel")


__plugin__ = Latina
