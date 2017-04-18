import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream


class Telefe(Plugin):
    _url_re = re.compile(r'https?://telefe.com/.+')

    @classmethod
    def can_handle_url(cls, url):
        return Telefe._url_re.match(url)

    def _get_streams(self):
        TELEFE_UA = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36 OPR/44.0.2510.1218"
        res = http.get(self.url, headers={'User-Agent': TELEFE_UA})
        busqueda_videoID = res.content.decode()
        busqueda_videoID = busqueda_videoID[busqueda_videoID.index('"PlayerContainer","model":{"id":') + 32 :]
        busqueda_videoID = busqueda_videoID[: busqueda_videoID.index(',')]
        #print('ID encontrado: ' + busqueda_videoID)

        hls_streams = HLSStream.parse_variant_playlist(
            self.session,
            "http://telefe.com/Api/Videos/GetSourceUrl/" + busqueda_videoID + "/0/HLS",
            headers={'Referer': self.url,
            'User-Agent': TELEFE_UA,
            'X-Requested-With': 'ShockwaveFlash/25.0.0.148'}
        )
        for s in hls_streams.items():
            yield s       


__plugin__ = Telefe
