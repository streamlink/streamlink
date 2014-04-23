import re

from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream, HDSStream
from livestreamer.utils import parse_xml

QUALITY_WEIGHTS = {
    "hd": 720,
    "veryhigh": 480,
    "high": 240,
    "med": 176,
    "low": 112
}

class zdf_mediathek(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return "zdf.de/ZDFmediathek" in url
       
    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "ZDFmediathek"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            self.logger.warning("rtmpdump is not usable, only HDS streams will be available")

        self.logger.debug("Fetching stream info")

        match = re.search("/\w*/(live|video)*/\d*", self.url)
        if match:
            a = match.group(0).split('/')
            stream_id = a[len(a)-1]
        else:
            raise NoStreamsError(self.url)
            
        api_url = "http://www.zdf.de/ZDFmediathek/xmlservice/web/beitragsDetails?ak=web&id={id}".format(id=stream_id)
        res = http.get(api_url)
        root = parse_xml(res.text.encode("utf8"))
        
        streams = {}
        for formitaet in root.iter('formitaet'):
            url = formitaet.find('url').text
            quality = formitaet.find('quality').text
                
            if formitaet.get('basetype') == "h264_aac_f4f_http_f4m_http":
                bb = re.search("http://(?:(?!\?).)*", url)
                hds_streams = HDSStream.parse_manifest(self.session, url)
                streams.update(hds_streams)
            elif formitaet.get('basetype') == 'h264_aac_mp4_rtmp_zdfmeta_http':
                streams[quality] = RTMPStream(self.session, {
                "rtmp": self._get_stream(url),
                "pageUrl": self.url,
                })
                
                
        return streams    
        
    
    def _get_stream(self, meta_url):
        res = http.get(meta_url)
        root = parse_xml(res.text.encode("utf8"))
        stream_url = root.find("default-stream-url").text
        return stream_url

__plugin__ = zdf_mediathek
