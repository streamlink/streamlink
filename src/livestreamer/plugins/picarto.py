from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.compat import urlparse
from livestreamer.utils import parse_qsd

class Picarto(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "picarto.tv" in url

    def _get_streams(self):
        params = parse_qsd(urlparse(self.url).query)
        if not 'watch' in params:
            raise NoStreamsError(self.url)
        channel = params['watch']
        
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable but required by Picarto plugin")
        
        streams = {}
        streams["live"] = RTMPStream(self.session, {
            "rtmp": "rtmp://199.189.86.17/dsapp/{0}.flv".format(channel),
            "pageUrl": self.url,
            "live": True
        })
        return streams
        
__plugin__ = Picarto