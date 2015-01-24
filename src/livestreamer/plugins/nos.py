"""Plugin for NOS: Nederlandse Omroep Stichting

Supports:
   MP$: http://nos.nl/uitzending/nieuwsuur.html
   Live: http://www.nos.nl/livestream/*
"""

import re
import json

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HTTPStream, HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?nos.nl/")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36"
}

_source_re = re.compile("<source(?P<source>[^>]+)>", re.IGNORECASE)
_source_src_re = re.compile("src=\"(?P<src>[^\"]+)\"", re.IGNORECASE)
_source_type_re = re.compile("type=\"(?P<type>[^\"]+)\"", re.IGNORECASE)


class NOS(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _resolve_stream(self):
        html = http.get(self.url, headers=HTTP_HEADERS).content
        data_stream = re.compile('data-stream="(.*?)"', re.DOTALL + re.IGNORECASE).search(html).group(1)

        resolve_data = {
            'stream': data_stream
        }

        data = http.post(
            'http://www-ipv4.nos.nl/livestream/resolve/',
            json=resolve_data,
            headers=HTTP_HEADERS
        ).json()

        js = http.get(data['url'], headers=HTTP_HEADERS).content
        js = re.compile('\((.*)\)').search(js).group(1)
        stream_url = json.loads(js)

        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_source_streams(self):
        html = http.get(self.url, headers=HTTP_HEADERS).content

        streams = {}
        sources = _source_re.findall(html)
        for source in sources:
            src = _source_src_re.search(source).group("src")
            pixels = _source_type_re.search(source).group("type")

            streams[pixels] = HTTPStream(self.session, src)

        return streams

    def _get_streams(self):
        urlparts = self.url.split('/')

        if urlparts[-2] == 'livestream':
            return self._resolve_stream()
        else:
            return self._get_source_streams()

__plugin__ = NOS
