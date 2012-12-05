from livestreamer.compat import urlparse
from livestreamer.stream import HLSStream
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.utils import urlget

from time import time
import re

class Streamingvideoprovider(Plugin):
    HLSStreamURL = "http://player.webvideocore.net/index.php"

    @classmethod
    def can_handle_url(self, url):
        return "streamingvideoprovider.co.uk" in url

    def _get_streams(self):
        channelname = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()
        streams = {}

        options = dict(l="info", a="ajax_video_info", file=channelname,
                       rid=time())
        res = urlget(self.HLSStreamURL, params=options)
        match = re.search("'(http://.+\.m3u8)'", res.text)

        if not match:
            raise NoStreamsError(self.url)

        playlisturl = match.group(1)
        self.logger.debug("Playlist URL is {0}", playlisturl)
        streams["live"] = HLSStream(self.session, playlisturl)

        return streams


__plugin__ = Streamingvideoprovider
