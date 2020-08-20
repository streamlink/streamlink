import re

from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils.url import update_scheme
from streamlink.exceptions import  NoStreamsError


class Nbcnews(Plugin):
    _url_re = re.compile(r'(?P<scheme>https?)://(?P<subdomain>\w+)\.?nbcnews.com/now(?P<path>.*)')
    _url_m3u8 = "https://api.leap.nbcsports.com/pid/NBCNews/220018/v4/desktop"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_playlist(self, data):
        """
        Get the playlist for live stream for nbcnews.com
        :return: string
        """
        try:
            url = data.get('videoSources', [{'cdnSources': {'primary': [{'sourceUrl': None}]}}])[0].get('cdnSources').get('primary')[0].get('sourceUrl')
        except:
            url = None

        return url

    def _get_streams(self):
        """
        Get the live stream for nbcnews.com
        :return:
        """
        match = self._url_re.match(self.url).groupdict()
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})

        if match.get("path") == "":
            res = self.session.http.get(self._url_m3u8)
            data = self.session.http.json(res)
            url = self._get_playlist(data)
            if url is None:
                raise NoStreamsError("Error get live stream url")

            for stream in HLSStream.parse_variant_playlist(self.session, url).items():
                yield stream

__plugin__ = Nbcnews


