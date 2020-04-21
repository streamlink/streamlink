import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class NBCNews(Plugin):
    url_re = re.compile(r'https?://(www.)?nbcnews.com/now')
    url_json = 'https://api.leap.nbcsports.com/pid/NBCNews/220018/v4/desktop'

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url_json)
        data = self.session.http.json(res)
        stream_url = data['videoSources'][0]['cdnSources']['primary'][0]['sourceUrl']
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = NBCNews
