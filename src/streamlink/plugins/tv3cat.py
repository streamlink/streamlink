#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.plugin.api import validate

STREAM_INFO_URL = "http://dinamics.ccma.cat/pvideo/media.jsp?media=video&version=0s&idint={ident}&profile=pc&desplacament=0"
_url_re = re.compile(r"http://(?:www.)?ccma.cat/tv3/directe/(.+?)/")
_media_schema = validate.Schema({
        "geo": validate.text,
        "url": validate.url(scheme=validate.any("http"))
    })
_channel_schema = validate.Schema({
    "media": validate.any([_media_schema], _media_schema)
    })


class TV3Cat(Plugin):
    @classmethod
    def can_handle_url(self, url):
        match = _url_re.match(url)
        return match

    def _get_streams(self):

        match = _url_re.match(self.url)
        if match:
            ident = match.group(1)
            data_url = STREAM_INFO_URL.format(ident=ident)

            # find the region, default to TOTS (international)
            res = http.get(self.url)
            geo_data = re.search(r'data-geo="([A-Z]+?)"', res.text)
            geo = geo_data and geo_data.group(1) or "TOTS"

            stream_data = http.json(http.get(data_url), schema=_channel_schema)

            # If there is only one item, it's not a list ... silly
            if isinstance(stream_data['media'], list):
                stream_infos = stream_data['media']
            else:
                stream_infos = [stream_data['media']]

            for stream in stream_infos:
                if stream['geo'] == geo:
                    return HLSStream.parse_variant_playlist(self.session, stream['url'])


__plugin__ = TV3Cat

