import re
import requests

from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

RTMP_URL = "rtmp://204.107.26.73/battlecam"
SWF_URL = "http://www.filmon.us/application/themes/base/flash/broadcast/VideoChatECCDN_debug_withoutCenteredOwner.swf"


class Filmon_us(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "filmon.us" in url

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon_us plugin")

        self.logger.debug("Fetching room_id")
        self.rsession = requests.session()
        res = urlget(self.url, session=self.rsession)

        match = re.search("room/id/(\d+)", res.text)
        if not match:
            return
        room_id = match.group(1)

        self.logger.debug("Comparing channel name with URL")
        match = re.search("<meta property=\"og:url\" content=\"http://www.filmon.us/(\w+)", res.text)
        if not match:
            return
        channel_name = match.group(1)
        base_name = self.url.rstrip("/").rpartition("/")[2]

        if (channel_name != base_name):
            return

        streams = {}
        try:
            streams['default'] = self._get_stream(room_id)
        except NoStreamsError:
            pass

        return streams

    def _get_stream(self, room_id):
        playpath = "mp4:bc_" + room_id
        if not playpath:
            raise NoStreamsError(self.url)

        rtmp = RTMP_URL
        parsed = urlparse(rtmp)
        if not parsed.scheme.startswith("rtmp"):
            raise NoStreamsError(self.url)

        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        return RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "playpath": playpath,
            "app": app,
            "live": True
        })

__plugin__ = Filmon_us
