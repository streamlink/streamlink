import re
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.stream import RTMPStream, HTTPStream
from streamlink.plugin.api import http


_streams_re = re.compile(r"""
    src:\s+"(
        rtmp://.*?\?t=.*?|                      # RTMP stream
        https?://.*?playlist.m3u8.*?\?t=.*?|    # HLS stream
        https?://.*?manifest.mpd.*?\?t=.*?|     # DASH stream
        https?://.*?.mp4\?t=.*?                 # HTTP stream
        )".*?
     type:\s+"(.*?)"                            # which stream type it is
     """, re.M | re.DOTALL | re.VERBOSE)
_url_re = re.compile(r"http(s)?://(?:\w+\.)?(livecoding|liveedu)\.tv")


class LivecodingTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _streams_re.findall(res.content.decode('utf-8'))
        for url, stream_type in match:
            if stream_type == "rtmp/mp4" and RTMPStream.is_usable(self.session):
                params = {
                    "rtmp": url,
                    "pageUrl": self.url,
                    "live": True,
                }
                yield 'live', RTMPStream(self.session, params)
            elif stream_type == "application/x-mpegURL":
                for s in HLSStream.parse_variant_playlist(self.session, url).items():
                    yield s
            elif stream_type == "video/mp4":
                yield 'vod', HTTPStream(self.session, url)


__plugin__ = LivecodingTV
