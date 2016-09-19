"""Plugin for NOS: Nederlandse Omroep Stichting

Supports:
   MP$: http://nos.nl/uitzending/nieuwsuur.html
   Live: http://www.nos.nl/livestream/*
   Tour: http://nos.nl/tour/live
"""

import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HTTPStream, HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?nos.nl/")
_js_re = re.compile('\((.*)\)')
_data_stream_re = re.compile('data-stream="(.*?)"', re.DOTALL | re.IGNORECASE)
_source_re = re.compile("<source(?P<source>[^>]+)>", re.IGNORECASE)
_source_src_re = re.compile("src=\"(?P<src>[^\"]+)\"", re.IGNORECASE)
_source_type_re = re.compile("type=\"(?P<type>[^\"]+)\"", re.IGNORECASE)


class NOS(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _resolve_stream(self):
        res = http.get(self.url)
        match = _data_stream_re.search(res.text)
        if not match:
            return
        data_stream = match.group(1)

        resolve_data = {
            'stream': data_stream
        }
        res = http.post(
            'http://www-ipv4.nos.nl/livestream/resolve/',
            data=json.dumps(resolve_data)
        )
        data = http.json(res)

        res = http.get(data['url'])
        match = _js_re.search(res.text)
        if not match:
            return

        stream_url = parse_json(match.group(1))

        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_source_streams(self):
        res = http.get(self.url)

        streams = {}
        sources = _source_re.findall(res.text)
        for source in sources:
            src = _source_src_re.search(source).group("src")
            pixels = _source_type_re.search(source).group("type")

            streams[pixels] = HTTPStream(self.session, src)

        return streams

    def _get_streams(self):
        urlparts = self.url.split('/')

        if urlparts[-2] == 'livestream' or urlparts[-3] == 'tour':
            return self._resolve_stream()
        else:
            return self._get_source_streams()

__plugin__ = NOS
