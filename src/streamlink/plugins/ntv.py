import re
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class NTV(Plugin):
    url_re = re.compile(r'https://www.ntv.ru/air/.*')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        body = self.session.http.get(self.url).text
        mrl_re = re.compile(r'var camHlsURL = \'(.*)\'')
        if mrl_re.search(body):
            MRL = 'http:' + mrl_re.search(body).group(1)
        else:
            mrl_re = re.compile(r'var hlsURL = \'(.*)\'')
            MRL = mrl_re.search(body).group(1)
        return HLSStream.parse_variant_playlist(self.session, MRL)

__plugin__ = NTV
