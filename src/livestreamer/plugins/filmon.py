import re
import requests

from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, urlopen, res_json

AJAX_HEADERS = {
    "Referer": "http://www.filmon.com",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
CHINFO_URL = "http://www.filmon.com/ajax/getChannelInfo"
SWF_URL = "http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"


class Filmon(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match("^http(s)?://(\w+\.)?filmon.com/tv/.+", url)

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon plugin")

        self.logger.debug("Fetching stream info")
        self.rsession = requests.session()
        res = urlget(self.url, session=self.rsession)

        match = re.search("/channels/(\d+)/extra_big_logo.png", res.text)
        if not match:
            return

        channel_id = match.group(1)
        streams = {}
        for quality in ("low", "high"):
            try:
                streams[quality] = self._get_stream(channel_id, quality)
            except NoStreamsError:
                pass

        return streams

    def _get_stream(self, channel_id, quality):
        params = dict(channel_id=channel_id, quality=quality)
        res = urlopen(CHINFO_URL, data=params, headers=AJAX_HEADERS,
                      session=self.rsession)
        json = res_json(res)

        if not json:
            raise NoStreamsError(self.url)
        elif not isinstance(json, list):
            raise PluginError("Invalid JSON response")

        info = json[0]
        rtmp = info.get("serverURL")
        playpath = info.get("streamName")
        if not (rtmp and playpath):
            raise NoStreamsError(self.url)

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

__plugin__ = Filmon
