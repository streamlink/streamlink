import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream


class TV1Channel(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?tv1channel\.org/(?!play/)(?:index\.php/livetv)?')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.FIREFOX})
        res = self.session.http.get(self.url)
        for iframe in itertags(res.text, 'iframe'):
            if 'cdn.netbadgers.com' not in iframe.attributes.get('src'):
                continue

            res = self.session.http.get(iframe.attributes.get('src'))
            for source in itertags(res.text, 'source'):
                if source.attributes.get('src') and source.attributes.get('src').endswith('.m3u8'):
                    return HLSStream.parse_variant_playlist(self.session,
                                                            source.attributes.get('src'))

            break


__plugin__ = TV1Channel
