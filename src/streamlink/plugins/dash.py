#!/usr/bin/env python
import logging

import re
from streamlink.plugin import Plugin
from streamlink.plugin.plugin import stream_weight
from streamlink.plugin.plugin import LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY
from streamlink.stream.dash import DASHStream
from streamlink.compat import urlparse

log = logging.getLogger(__name__)


class MPEGDASH(Plugin):
    _url_re = re.compile(r"(dash://)?(.+(?:\.mpd)?.*)")

    @classmethod
    def priority(cls, url):
        """
        Returns LOW priority if the URL is not prefixed with dash:// but ends with
        .mpd and return NORMAL priority if the URL is prefixed.
        :param url: the URL to find the plugin priority for
        :return: plugin priority for the given URL
        """
        m = cls._url_re.match(url)
        if m:
            prefix, url = cls._url_re.match(url).groups()
            url_path = urlparse(url).path
            if prefix is None and url_path.endswith(".mpd"):
                return LOW_PRIORITY
            elif prefix is not None:
                return NORMAL_PRIORITY
        return NO_PRIORITY

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

__plugin__ = MPEGDASH
