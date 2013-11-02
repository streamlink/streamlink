from livestreamer.compat import urlparse, urljoin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, urlopen, parse_json

import re
import requests

class Filmon(Plugin):
    SWFURL = "http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"
    CHINFO = "http://www.filmon.com/ajax/getChannelInfo"

    @classmethod
    def can_handle_url(self, url):
        return "filmon.com" in url

    def _get_streams(self):

        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon plugin")

        self.logger.debug("Fetching stream info")

        self.rsession = requests.session()
        res = urlget(self.url, session=self.rsession)

        match = re.search("/channels/(\d+)/extra_big_logo.png", res.text)
        if match:
            channel_id = match.group(1)
        else:
            raise NoStreamsError(self.url)

        streams = {}
        streams.update(self._get_stream(channel_id, "low"))
        try:
            streams.update(self._get_stream(channel_id, "high"))
        except:
            pass

        return streams

    def _get_stream(self, channel_id, quality):

        headers = {
            "Referer": "http://www.filmon.com",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        }

        params = dict(channel_id=channel_id, quality=quality)

        res = urlopen(self.CHINFO, data=params, headers=headers,
                      session=self.rsession)

        if res:
            json = parse_json(res.text)
        else:
            raise NoStreamsError(self.url)

        if not isinstance(json, list):
            raise PluginError("Invalid JSON response")
        elif not len(json) > 0:
            raise NoStreamsError(self.url)
        elif not ("serverURL" in json[0] and "streamName" in json[0]):
            raise NoStreamsError(self.url)

        rtmp = json[0]["serverURL"]
        playpath = json[0]["streamName"]
        parsed = urlparse(rtmp)

        if not parsed.scheme.startswith("rtmp"):
            raise NoStreamsError(self.url)

        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        stream = {}
        stream[quality] = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfUrl": self.SWFURL,
            "playpath": playpath,
            "app": app,
            "live": True
        })

        return stream


__plugin__ = Filmon
