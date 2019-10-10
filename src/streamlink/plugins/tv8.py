from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class TV8(Plugin):
    """
    Support for the live stream on www.tv8.com.tr
    """
    url_re = re.compile(r"https?://www.tv8.com.tr/canli-yayin")

    player_config_re = re.compile(r'''file:\s*"(.*?)"''')
    player_config_schema = validate.Schema(
        validate.transform(player_config_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.url()
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        stream_url = self.player_config_schema.validate(res.text)
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = TV8
