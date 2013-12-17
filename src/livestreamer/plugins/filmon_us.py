import re
import requests

from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HTTPStream
from livestreamer.utils import urlget, urlresolve, prepend_www

RTMP_URL = "rtmp://204.107.26.73/battlecam"
RTMP_UPLOAD_URL = "rtmp://204.107.26.75/streamer"
SWF_URL = "http://www.filmon.us/application/themes/base/flash/broadcast/VideoChatECCDN_debug_withoutCenteredOwner.swf"
SWF_UPLOAD_URL = "http://www.battlecam.com/application/themes/base/flash/MediaPlayer.swf"


class Filmon_us(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "filmon.us" in url

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon_us plugin")

        streams = {}

        try:
            # history video
            if "filmon.us/history" in self.url or "filmon.us/video/history/hid" in self.url:
                streams['default'] = self._get_history()
            # uploaded video
            elif "filmon.us/video" in self.url:
                streams['default'] = self._get_stream_upload()
            # live video
            else:
                streams['default'] = self._get_stream_live()
        except NoStreamsError:
            pass

        return streams

    def _get_history(self):
        video_id = self.url.rstrip("/").rpartition("/")[2]

        self.logger.debug("Testing if video exist")
        history_url = 'http://www.filmon.us/video/history/hid/' + video_id
        if urlresolve(prepend_www(history_url)) == '/':
            raise PluginError("history number " + video_id + " don't exist")

        self.logger.debug("Fetching video URL")
        res = urlget(history_url)
        match = re.search("http://cloud.battlecam.com/([/\w]+).flv", res.text)
        if not match:
            return
        url = match.group(0)

        return HTTPStream(self.session, url)

    def _get_stream_upload(self):
        video = urlparse(self.url).path

        if urlresolve(prepend_www(self.url)) == 'http://www.filmon.us/channels':
            raise PluginError(video + " don't exist")

        playpath = "mp4:resources" + video + '/v_3.mp4'

        rtmp = RTMP_UPLOAD_URL
        parsed = urlparse(rtmp)
        app = parsed.path[1:]

        return RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfUrl": SWF_UPLOAD_URL,
            "playpath": playpath,
            "app": app,
            "live": True
        })

    def _get_stream_live(self):
        self.logger.debug("Fetching room_id")
        res = urlget(self.url)
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

        playpath = "mp4:bc_" + room_id
        if not playpath:
            raise NoStreamsError(self.url)

        rtmp = RTMP_URL
        parsed = urlparse(rtmp)
        app = parsed.path[1:]

        return RTMPStream(self.session, {
            "rtmp": RTMP_URL,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "playpath": playpath,
            "app": app,
            "live": True
        })

__plugin__ = Filmon_us
