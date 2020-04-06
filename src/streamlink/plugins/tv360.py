from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class TV360(Plugin):
    url_re = re.compile(r"https?://(?:www.)?tv360.com.tr/canli-yayin")
    hls_re = re.compile(r'''hls.loadSource\(["'](http.*m3u8)["']\)''', re.DOTALL)

    hls_schema = validate.Schema(
        validate.transform(hls_re.search),
        validate.any(None, validate.all(validate.get(1)))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        hls_url = self.hls_re.search(res.text)

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url.group(1))


__plugin__ = TV360
