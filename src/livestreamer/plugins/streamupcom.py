import re

from livestreamer.compat import urljoin
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream, HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?streamup.com/(?P<channel>[^/?]+)")
_hls_manifest_re = re.compile('HlsManifestUrl:\\s*"//"\\s*\\+\\s*response\\s*\\+\\s*"(.+)"')

class StreamupCom(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        if not res: return
        match = _hls_manifest_re.search(res.text)
        url = match.group(1)
        hls_url = "http://video-cdn.streamup.com{}".format(url)
        return HLSStream.parse_variant_playlist(self.session, hls_url)

__plugin__ = StreamupCom
