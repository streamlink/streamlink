from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class RaiPlay(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?raiplay\.it/dirette/(\w+)/?")
    stream_re = re.compile(r"data-video-url.*?=.*?\"([^\"]+)\"")
    stream_schema = validate.Schema(
        validate.all(
            validate.transform(stream_re.search),
            validate.any(
                None,
                validate.all(validate.get(1), validate.url())
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        channel = self.url_re.match(self.url).group(1)
        self.logger.debug("Found channel: {0}", channel)
        stream_url = http.get(self.url, schema=self.stream_schema)
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url, headers={"User-Agent": useragents.CHROME})


__plugin__ = RaiPlay
