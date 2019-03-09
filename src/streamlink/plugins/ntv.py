import re
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class NTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?ntv.ru/air/$")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        tns = 'http://www.ntv.ru/services/live/tns/'
        body = self.session.http.get(tns).text
        d = {}
        exec(body, d)
        mrl = d['hls']
        return HLSStream.parse_variant_playlist(self.session, mrl)

__plugin__ = NTV
