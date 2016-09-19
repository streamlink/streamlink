import re

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import http
from streamlink.stream import HLSStream

# The last four channel_paths repsond with 301 and provide
# a redirect location that corresponds to a channel_path above.
_url_re = re.compile(r"""
    https?://www\.rtve\.es/
    (?P<channel_path>
        directo/la-1|
        directo/la-2|
        directo/teledeporte|
        directo/canal-24h|

        noticias/directo-la-1|
        television/la-2-directo|
        deportes/directo/teledeporte|
        noticias/directo/canal-24h
    )
    /?
""", re.VERBOSE)

_id_map = {
    "directo/la-1": "LA1",
    "directo/la-2": "LA2",
    "directo/teledeporte": "TDP",
    "directo/canal-24h": "24H",
    "noticias/directo-la-1": "LA1",
    "television/la-2-directo": "LA2",
    "deportes/directo/teledeporte": "TDP",
    "noticias/directo/canal-24h": "24H",
}


class Rtve(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def __init__(self, url):
        Plugin.__init__(self, url)
        match = _url_re.match(url).groupdict()
        self.channel_path = match["channel_path"]

    def _get_streams(self):
        stream_id = _id_map[self.channel_path]
        hls_url = "http://iphonelive.rtve.es/{0}_LV3_IPH/{0}_LV3_IPH.m3u8".format(stream_id)

        # Check if the stream is available
        res = http.head(hls_url, raise_for_status=False)
        if res.status_code == 404:
            raise PluginError("The program is not available due to rights restrictions")

        return HLSStream.parse_variant_playlist(self.session, hls_url)

__plugin__ = Rtve
