from livestreamer.stream import HLSStream
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.utils import urlget

from time import time
import re

class Streamingvideoprovider(Plugin):
    HLSStreamURL = "http://player.webvideocore.net/index.php?l=info&a=ajax_video_info&file={0}&rid={1}"

    @classmethod
    def can_handle_url(self, url):
        return "streamingvideoprovider.co.uk" in url

    def _get_streams(self):
        channelname = self.url.rstrip("/").rpartition("/")[2].lower()
        unixtime = str(int(time()))
        try:
            res = urlget(self.HLSStreamURL.format(channelname, unixtime))
            PlaylistURL = re.search("'(http://.+\.m3u8)'", res.text).group(1)
            self.logger.info("PlaylistURL is {0}".format(PlaylistURL))
            streams = {}
            streams['live'] = HLSStream(self.session, PlaylistURL)
        except IOError:
            raise NoStreamsError(self.url)

        return streams


__plugin__ = Streamingvideoprovider
