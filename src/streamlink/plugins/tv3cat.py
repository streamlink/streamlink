#!/usr/bin/env python
import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.plugin.api import validate

log = logging.getLogger(__name__)


class TV3Cat(Plugin):
    _url_re = re.compile(r"http://(?:www.)?ccma.cat/tv3/directe/(.+?)/")
    _stream_info_url = "http://dinamics.ccma.cat/pvideo/media.jsp?media=video&version=0s&idint={ident}&profile=pc&desplacament=0"
    _media_schema = validate.Schema({
        "geo": validate.text,
        "url": validate.url(scheme=validate.any("http", "https"))
    })
    _channel_schema = validate.Schema({
        "media": validate.any([_media_schema], _media_schema)},
        validate.get("media"),
        # If there is only one item, it's not a list ... silly
        validate.transform(lambda x: x if isinstance(x, list) else [x])
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        if match:
            ident = match.group(1)
            data_url = self._stream_info_url.format(ident=ident)
            stream_infos = self.session.http.json(self.session.http.get(data_url), schema=self._channel_schema)

            for stream in stream_infos:
                try:
                    return HLSStream.parse_variant_playlist(self.session, stream['url'], name_fmt="{pixels}_{bitrate}")
                except:
                    log.debug("Failed to get streams for: {0}".format(stream['geo']))
                    pass


__plugin__ = TV3Cat
