import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream


class CNEWS(Plugin):
    _url_re = re.compile(r'(https|http)://www.cnews.fr/(.*)')
    _embed_video_url_re = re.compile(r'class="dm-video-embed_video" src="(?P<dm_url>)"')
    _embed_live_url_re = re.compile(r'class="wrapper-live-player main-live-player"><iframe src="(?P<dm_url>)"')

    @classmethod
    def can_handle_url(cls, url):
        return CNEWS._url_re.match(url)

    def _get_streams(self):
        # Retrieve URL page and search for Dailymotion URL
        res = http.get(self.url, headers={'User-Agent' : useragents.CHROME})
        match = self._embed_live_url_re.search(res.text) or self._embed_video_url_re.search(res.text)
        if match is not None:
            for stream in self.session.streams(match.group('dm_url')).items():
                yield stream


__plugin__ = CNEWS
