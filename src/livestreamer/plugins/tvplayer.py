#!/usr/bin/env python
import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream

USER_AGENT_STRING = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/43.0.2357.65 Safari/537.36")
STREAM_INFO_URL = "http://lapi.cdn.tvplayer.com/tvplayer/stream/live/id/{id}"
_url_re = re.compile(r"http://(?:www.)?tvplayer.com/watch/(.+)")
_channel_map_re = re.compile(r'href="/watch/([a-z]+?)".*?img.*?src=".*?/(\d+).png"', re.S)
_channel_schema = validate.Schema({
    "stream": validate.url(scheme=validate.any("http"))
})


class TVPlayer(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        match = _url_re.match(url)
        return match

    def _get_streams(self):
        url_match = _url_re.match(self.url)
        if url_match:
            # find the list of channels from the html in the page
            res = http.get(self.url)
            channel_map = dict(_channel_map_re.findall(res.text))
            channel_id = channel_map.get(url_match.group(1))

            # get the stream urls
            res = http.get(STREAM_INFO_URL.format(id=channel_id))
            stream_data = http.json(res, schema=_channel_schema)

            return HLSStream.parse_variant_playlist(self.session,
                                                    stream_data['stream'],
                                                    headers={'user-agent': USER_AGENT_STRING})


__plugin__ = TVPlayer

