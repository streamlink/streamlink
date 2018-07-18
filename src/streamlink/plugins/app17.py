import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream, RTMPStream, HTTPStream

API_URL = "https://api-dsa.17app.co/api/v1/liveStreams/getLiveStreamInfo"

_url_re = re.compile(r"https://17.live/live/(?P<channel>[^/&?]+)")
_status_re = re.compile(r'\\"closeBy\\":\\"\\"')
_rtmp_re = re.compile(r'\\"url\\"\s*:\s*\\"(.+?)\\"')


class App17(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        self.session.http.headers.update({'User-Agent': useragents.CHROME})

        payload = '{"liveStreamID": "%s"}' % (channel)
        res = self.session.http.post(API_URL, data=payload)
        status = _status_re.search(res.text)
        if not status:
            self.logger.info("Stream currently unavailable.")
            return

        http_url = _rtmp_re.search(res.text).group(1)
        http_url = http_url.replace("http:", "https:")
        yield "live", HTTPStream(self.session, http_url)

        if 'pull-rtmp' in http_url:
            url = http_url.replace("https:", "rtmp:").replace(".flv", "")
            stream = RTMPStream(self.session, {
                "rtmp": url,
                "live": True
            })
            yield "live", stream

        if 'wansu-' in http_url:
            url = http_url.replace(".flv", "/playlist.m3u8")
            for stream in HLSStream.parse_variant_playlist(self.session, url).items():
                yield stream
        else:
            url = http_url.replace("live-hdl", "live-hls").replace(".flv", ".m3u8")
            yield "live", HLSStream(self.session, url)


__plugin__ = App17
