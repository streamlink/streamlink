import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json


class Telefe(Plugin):
    _url_re = re.compile(r'https?://telefe.com/.+')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, headers={'User-Agent': useragents.CHROME})
        busqueda_video = res.text
        busqueda_video = busqueda_video[busqueda_video.index('{"top":{"view":"PlayerContainer","model":{'):]
        busqueda_video = busqueda_video[: busqueda_video.index('}]}}') +4] + "}"
        
        url_video_encontrado_hls  = ""
        url_video_encontrado_http = ""

        json_busqueda_video = parse_json(busqueda_video)
        json_busqueda_video_sources = json_busqueda_video["top"]["model"]["videos"][0]["sources"]
        self.logger.debug('ID encontrado: {0}', json_busqueda_video["top"]["model"]["id"])
        for video_source_actual in json_busqueda_video_sources:
            if "HLS" in video_source_actual["type"]:
                url_video_encontrado_hls = "http://telefe.com" + video_source_actual["url"]
                self.logger.debug("Contenido HLS disponible")
            if "HTTP" in video_source_actual["type"]:
                url_video_encontrado_http = "http://telefe.com" + video_source_actual["url"]
                self.logger.debug("Contenido HTTP disponible")
        
        http.headers = {'Referer': self.url,
            'User-Agent': useragents.CHROME,
            'X-Requested-With': 'ShockwaveFlash/25.0.0.148'}
            
        if url_video_encontrado_hls:
            hls_streams = HLSStream.parse_variant_playlist(self.session, url_video_encontrado_hls)
            for s in hls_streams.items():
                yield s  

        if url_video_encontrado_http:
            yield "http", HTTPStream(self.session, url_video_encontrado_http)   
               


__plugin__ = Telefe
