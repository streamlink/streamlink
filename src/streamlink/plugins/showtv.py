from __future__ import print_function

import json
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class ShowTV(Plugin):
    """
    Support for the live stream on www.showtv.com.tr
    """
    url_re = re.compile(r"https?://www.showtv.com.tr/canli-yayin/showtv")
    stream_re = re.compile(r"""div .*? data-ht=(?P<quote>["'])(?P<data>.*?)(?P=quote)""", re.DOTALL)
    stream_data_schema = validate.Schema(
        validate.transform(stream_re.search),
        validate.any(
            None,
            validate.all(
                validate.get("data"),
                validate.transform(json.loads),
                {
                    "ht_stream_m3u8": validate.url()
                },
                validate.get("ht_stream_m3u8")
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        stream_url = self.stream_data_schema.validate(res.text)
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = ShowTV
