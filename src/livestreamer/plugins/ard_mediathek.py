import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HTTPStream, HDSStream, RTMPStream
from livestreamer.utils import verifyjson
from livestreamer.exceptions import NoStreamsError, PluginError, StreamError

PAGE_URL = "http://www.ardmediathek.de/tv"
SWF_URL = "http://www.ardmediathek.de/ard/static/player/base/flash/PluginFlash.swf"
CONFIG_URL = "http://www.ardmediathek.de/play/media/{0}"
HDCORE_PARAMETER = "?hdcore=3.3.0"
QUALITY_MAP = {
    "auto": "auto",
    3: "544p",
    2: "360p",
    1: "288p",
    0: "144p"
}

class ard_mediathek(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return "ardmediathek.de/tv" in url.lower()
        
    def _get_mp4_streams(self, streamname, quality):
        url = streamname
        self.logger.debug("Stream URL: " + url)
        qualityname = QUALITY_MAP[quality]
        self.logger.debug("Quality: " + qualityname)
        tmpstreams = {}
        tmpstreams[qualityname] = HTTPStream(self.session, url)
        return tmpstreams
    
    def _get_smil_streams(self, streamname):
        res = http.get(streamname)
        smil = http.xml(res, "SMIL config")
        httpbase = smil.find("head/meta").attrib.get("base")
        videos = smil.findall("body/seq/video")
            
        for video in videos:
            src = video.attrib.get("src")
            self.logger.debug(src)
            url = httpbase + src + HDCORE_PARAMETER
            self.logger.debug("Stream URL: " + url)
            tmpstreams = {}
            try:
                tmpstreams = HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL)
            except IOError as err:
                self.logger.warning("Failed to get HDS manifest: {0}", err)
            return tmpstreams
    
    def _get_f4m_streams(self, streamname):
        '''
        needs to hdcore parameter set to work. 
        '''
        url = streamname + HDCORE_PARAMETER
        self.logger.debug("Stream URL: " + url)
        tmpstreams = {}
        try:
            tmpstreams = HDSStream.parse_manifest(self.session, url, pvswf=SWF_URL)
        except IOError as err:
            self.logger.warning("Failed to get HDS manifest: {0}", err)
        return tmpstreams
    
    def _get_rtmp_streams(self, servername, streamname, quality):
        '''
        for some streams they used invalid urls with slashes missing. this is a 
        fix for that problem. here is an example
        http://www.ardmediathek.de/tv/live?kanal=1386988
        http://www.ardmediathek.de/play/media/15806928?devicetype=pc&features=flash
        '''        
        if servername.endswith("/"):
            if streamname.startswith("/"):
                self.logger.debug("URL invalid")
                url = servername[:-1] + streamname
            else:
                self.logger.debug("URL valid")
                url = servername + streamname
        else:
            if streamname.startswith("/"):
                self.logger.debug("URL valid")
                url = servername + streamname
            else:
                self.logger.debug("URL invalid")
                url = servername + "/" + streamname
            
        self.logger.debug("Stream URL: " + url)
        qualityname = QUALITY_MAP[quality]
        self.logger.debug("Quality: " + qualityname)
        tmpstreams = {}
        tmpstreams[qualityname] = RTMPStream(self.session, {
            "rtmp": url,
            "pageUrl": PAGE_URL,
            "swfVfy": SWF_URL,
            "live": True
        })
        return tmpstreams
        
    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = http.get(self.url)
        
        match = re.search("/play/config/(\d+)", res.text)
        if match:
            self.logger.debug("Stream ID: " + match.group(1))
            streamid = match.group(1)
        else:
            return
        
        self.logger.debug("Config URL: " + CONFIG_URL.format(streamid))
        res = http.get(CONFIG_URL.format(streamid))
        json = http.json(res)
        mediaArray = verifyjson(json, "_mediaArray")
        
        streams = {}
        for media in mediaArray:
            mediaStreamArray = verifyjson(media, "_mediaStreamArray")
            for mediaStream in mediaStreamArray:
                try:
                    jsonvalid = True
                    flash = verifyjson(mediaStream, "flashUrl")
                    quality = verifyjson(mediaStream, "_quality")
                    '''
                    there is one channel where the servername is incorrect. it has
                    spaces on the beginning. stripping whitespaces on both the server 
                    and the stream name just for good measures. here is an example
                    http://www.ardmediathek.de/tv/live?kanal=1386988
                    http://www.ardmediathek.de/play/media/15806928?devicetype=pc&features=flash
                    '''
                    server = verifyjson(mediaStream, "_server").strip()
                    stream = verifyjson(mediaStream, "_stream").strip()
                except PluginError:
                    '''
                    there are some odd json respones where parts are missing and 
                    instead of one video in _stream there is a list. this just igores
                    them for now. here is an expample:
                    http://www.ardmediathek.de/play/media/21897740
                    http://www.ardmediathek.de/tv/FIFA-WM-2014/Bundestrainer-L%C3%B6w-lobt-M%C3%BCller/Das-Erste/Video?documentId=21897740&bcastId=21675666
                    '''
                    self.logger.debug("odd json format. ignoring this stream format")
                    jsonvalid = False
                    pass
                if flash is True and server.startswith("rtmp://") and jsonvalid:
                    self.logger.debug("RTMP stream")
                    tmpstreams = self._get_rtmp_streams(server, stream, quality)
                    streams.update(tmpstreams)
                elif stream.endswith(".f4m") and jsonvalid:
                    self.logger.debug("F4M manifest")
                    tmpstreams = self._get_f4m_streams(stream)
                    streams.update(tmpstreams)
                elif stream.endswith(".smil") and jsonvalid:
                    self.logger.debug("SMIL playlist")
                    tmpstreams = self._get_smil_streams(stream)
                    streams.update(tmpstreams)
                elif stream.endswith(".mp4") and jsonvalid:
                    self.logger.debug("MP4 video")
                    tmpstreams = self._get_mp4_streams(stream, quality)
                    streams.update(tmpstreams)
                else:
                    self.logger.debug("format not supported yet")
                        
        return streams

__plugin__ = ard_mediathek
