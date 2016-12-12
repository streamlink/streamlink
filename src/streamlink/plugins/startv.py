from __future__ import print_function

import json
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class StarTV(Plugin):
    """
    Support for the Live Stream from www.startv.com.tr, only the mobile stream (HLS) is supported as the HDS stream
    has some kind of token authentication.

    TODO: support HDS streams
    """
    url_re = re.compile(r"http://www.startv.com.tr/canli-yayin")
    playervars_re = re.compile(r"mobileUrl: \"(.*?)\"")
    token_schema = validate.Schema(
        validate.transform(playervars_re.search),  # search the playerArray variable
        validate.any(
            None,
            validate.all(
                validate.get(1),  # get the first match
                validate.url(),
            )
        )
    )
    api_schema = validate.Schema(validate.all(
        {
            "success": True,
            "xtra": {"url": validate.url()}
        },
        validate.get("xtra"), validate.get("url")
    ))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self.url)
        mobile_url = self.token_schema.validate(res.text)
        if mobile_url:
            return HLSStream.parse_variant_playlist(self.session, mobile_url, headers={"Referer": self.url})

__plugin__ = StarTV
