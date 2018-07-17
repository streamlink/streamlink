import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import RTMPStream
from streamlink.stream import HLSStream

PAGE_URL = "https://www.tigerdile.com/stream/"
ROOT_URL = "rtmp://stream.tigerdile.com/live/{0}"
API_URL = "https://api.tigerdile.com/video?key={channel}"
HLS_URL = "https://outbound.tigerdile.com/{channel}/index.m3u8"
STREAM_TYPES = ["rtmp"]

_url_re = re.compile(r"""
    https?://(?:www|sfw)\.tigerdile\.com
    \/stream\/(.+)\/?""", re.VERBOSE)


class Tigerdile(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = self.url
        streamname = _url_re.search(res).group(1)

        ci = self.session.http.get(API_URL.format(channel=streamname))
        api_json = json.loads(ci.text)

        if not api_json or len(api_json) == 0:
            self.logger.error("The channel {0} does not exist or is marked private".format(streamname))
            return

        if api_json[0]["online"] == False:
            self.logger.error("The channel {0} is not online".format(streamname))
            return

        streams = {}
        stream = RTMPStream(self.session, {
            "rtmp": ROOT_URL.format(streamname),
            "pageUrl": PAGE_URL,
            "live": True,
            "app": "live",
            "flashVer": "LNX 11,2,202,280",
            "swfVfy": "https://www.tigerdile.com/wp-content/jwplayer.flash.swf",
            "playpath": streamname,
        })
        streams["live"] = stream

        stream_hls = HLSStream(self.session, HLS_URL.format(channel=streamname))
        streams["live_hls"] = stream_hls

        return streams


__plugin__ = Tigerdile
