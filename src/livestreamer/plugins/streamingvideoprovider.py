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
        channelname = self.url.rstrip("/").rpartition("/")[2].lower()
        streams = {}

        try:
            options = dict(l="info", a="ajax_video_info", file=channelname,
                           rid=time())

            res = urlget(self.HLSStreamURL, params=options, exception=IOError)
            match = re.search("'(http://.+\.m3u8)'", res.text)

            if not match:
                raise PluginError("Failed to find HLS playlist in result")

            playlisturl = match.group(1)

            self.logger.debug("Playlist URL is {0}", playlisturl)

            streams["live"] = HLSStream(self.session, playlisturl)
        except IOError:
            raise NoStreamsError(self.url)

        return streams


__plugin__ = Streamingvideoprovider
