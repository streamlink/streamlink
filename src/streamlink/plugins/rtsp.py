import re

from streamlink.plugin import Plugin
from streamlink.stream.ffmpegmux import FFMPEGMuxer


class FFMPEGRTSPPlugin(Plugin):
    _url_re = re.compile(r"(?P<url>rtsp://.+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        return {"rtsp_stream": FFMPEGMuxer(self.session, *(self.url,), is_muxed=False)}


__plugin__ = FFMPEGRTSPPlugin
