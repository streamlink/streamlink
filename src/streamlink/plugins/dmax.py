import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class Dmax(Plugin):
    _url_re = re.compile(r'(?P<scheme>https?)://(?P<subdomain>\w+)\.?dmax.de/(?P<path>programme/[\w\-]+/video/(?P<episode>[\w\-]+)/[\w\-]+)')
    _re_vod_hls = re.compile(r'streamUrlHls\":\"(?P<hls>.*)\",\"stream')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_vod_stream(self):
        """
        Find the VOD video url
        :return: video url
        """
        res = self.session.http.get(self.url)
        video_urls = self._re_vod_hls.findall(res.text)
        if len(video_urls):
            return HLSStream.parse_variant_playlist(self.session, video_urls[0])

    def _get_streams(self):
        """
        Find the streams for dmax.de
        :return:
        """
        match = self._url_re.match(self.url)

        episode = match.group('episode')
        if episode is not None:
            return self._get_vod_stream()


__plugin__ = Dmax
