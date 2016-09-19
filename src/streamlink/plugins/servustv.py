#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.stream import HDSStream

_channel = dict(
    at="servustvhd_1@51229",
    de="servustvhdde_1@75540"
)

STREAM_INFO_URL = "http://hdiosstv-f.akamaihd.net/z/{channel}/manifest.f4m"
_url_re = re.compile(r"http://(?:www.)?servustv.com/(de|at)/.*")


class ServusTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        match = _url_re.match(url)
        return match

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            if url_match.group(1) in _channel:
                return HDSStream.parse_manifest(self.session, STREAM_INFO_URL.format(channel=_channel[url_match.group(1)]))


__plugin__ = ServusTV
