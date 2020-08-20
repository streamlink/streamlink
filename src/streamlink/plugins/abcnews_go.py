import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream


class AbcnewsGo(Plugin):
    _url_re = re.compile(r'https?://(www\.)?abcnews\.go\.com/live(.*)?')
    _url_m3u8 = "https://abcnews.go.com/video/itemfeed?id=abc_live11&secure=true"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url.lower())

    def _get_playlist(self, data):
        """
        Get the playlist for live stream for abcnews.go.com
        :return: string
        """
        url = None
        try:
            mediaContent = data.get('channel', {'item': {'media-group': {'media-content': []}}}).get('item').get('media-group').get('media-content')
            for content in mediaContent:
                attributes = content.get('@attributes', {'type': {}})
                mediaContentType = attributes.get('type')
                url = attributes.get('url', "")
                if mediaContentType == 'application/x-mpegURL' and not 'preview' in url:
                    return url
        except Exception as err:
            pass

        return url

    def _get_streams(self):
        """
        Get the live stream for nbcnews.com
        :return:
        """
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        res = self.session.http.get(self._url_m3u8)
        data = self.session.http.json(res)
        url = self._get_playlist(data)

        for s in HLSStream.parse_variant_playlist(self.session, url).items():
            yield s

__plugin__ = AbcnewsGo