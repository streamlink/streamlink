#!/usr/bin/env python
import logging

import re
from streamlink.plugin import Plugin
from streamlink.plugin.plugin import stream_weight
from streamlink.stream.dash import DASHStream

log = logging.getLogger(__name__)


class DASHPlugin(Plugin):
    _url_re = re.compile(r"dash://(http://.*)")

    @classmethod
    def stream_weight(cls, stream):
        match = re.match("^(.*)+a(\d+)k$", stream)
        if match and match.group(2):
            weight, group = stream_weight(match.group(1))
            weight += int(match.group(2))
            return weight, group
        else:
            return stream_weight(stream)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        mpdurl = self._url_re.match(self.url).group(1)

        return DASHStream.parse_manifest(self.session, mpdurl)

__plugin__ = DASHPlugin
