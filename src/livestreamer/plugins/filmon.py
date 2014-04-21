import re

from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream

AJAX_HEADERS = {
    "Referer": "http://www.filmon.com",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
CHINFO_URL = "http://www.filmon.com/ajax/getChannelInfo"
VODINFO_URL = "http://www.filmon.com/vod/info/{0}"
QUALITY_WEIGHTS = {
    "high": 720,
    "low": 480
}
SWF_URL = "http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"


class Filmon(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return re.match("^http(s)?://(\w+\.)?filmon.com/(tv|vod).+", url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "filmon"

        return Plugin.stream_weight(key)

    def _get_rtmp_app(self, rtmp):
        parsed = urlparse(rtmp)
        if not parsed.scheme.startswith("rtmp"):
            return

        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        return app

    def _get_streams(self):
        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon plugin")

        self.logger.debug("Fetching stream info")
        res = http.get(self.url)

        match = re.search("movie_id=(\d+)", res.text)
        if match:
            return self._get_vod_stream(match.group(1))

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
        res = http.post(CHINFO_URL, data=params, headers=AJAX_HEADERS)
        json = http.json(res)

        if not json:
            raise NoStreamsError(self.url)
        elif not isinstance(json, list):
            raise PluginError("Invalid JSON response")

        info = json[0]
        rtmp = info.get("serverURL")
        playpath = info.get("streamName")
        if not (rtmp and playpath):
            raise NoStreamsError(self.url)

        app = self._get_rtmp_app(rtmp)
        if not app:
            raise NoStreamsError(self.url)

        return RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "playpath": playpath,
            "app": app,
            "live": True
        })

    def _get_vod_stream(self, movie_id):
        res = http.get(VODINFO_URL.format(movie_id), headers=AJAX_HEADERS)
        json = http.json(res)
        json = json and json.get("data")
        json = json and json.get("streams")

        if not json:
            raise NoStreamsError(self.url)

        streams = {}
        for quality in ("low", "high"):
            stream = json.get(quality)
            if not stream:
                continue

            rtmp = stream.get("url")
            app = self._get_rtmp_app(rtmp)
            if not app:
                continue

            playpath = stream.get("name")
            if ".mp4" in playpath:
                playpath = "mp4:" + playpath

            streams[quality] = RTMPStream(self.session, {
                "rtmp": rtmp,
                "pageUrl": self.url,
                "swfUrl": SWF_URL,
                "playpath": playpath,
                "app": app,
            })

        return streams


__plugin__ = Filmon
