import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class NTV(Plugin):
    url_re = re.compile(r'https?://www.ntv.ru/air/.*')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        body = self.session.http.get(self.url).text
        mrl = None
        match = re.search(r'var camHlsURL = \'(.*)\'', body)
        if match:
            mrl = 'http:' + match.group(1)
        else:
            match = re.search(r'var hlsURL = \'(.*)\'', body)
            if match:
                mrl = match.group(1)
        if mrl:
            return HLSStream.parse_variant_playlist(self.session, mrl)


__plugin__ = NTV
