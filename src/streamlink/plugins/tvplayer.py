#!/usr/bin/env python
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream


class TVPlayer(Plugin):
    _user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/43.0.2357.65 Safari/537.36")
    API_URL = "http://api.tvplayer.com/api/v2/stream/live"
    _url_re = re.compile(r"http://(?:www.)?tvplayer.com/watch/(.+)")
    _stream_attrs_ = re.compile(r'var\s+(validate|platform|resourceId)\s+=\s*(.*?);', re.S)
    _stream_schema = validate.Schema({
        "tvplayer": validate.Schema({
            "status": u'200 OK',
            "response": validate.Schema({
                "stream": validate.url(scheme=validate.any("http"))
            })
        })
    })

    @classmethod
    def can_handle_url(cls, url):
        match = TVPlayer._url_re.match(url)
        return match

    def _get_streams(self):
        # find the list of channels from the html in the page
        res = http.get(self.url)
        stream_attrs = dict((k, v.strip('"')) for k, v in TVPlayer._stream_attrs_.findall(res.text))

        # get the stream urls
        res = http.post(TVPlayer.API_URL, data=dict(id=stream_attrs["resourceId"],
                                                    validate=stream_attrs["validate"],
                                                    platform=stream_attrs["platform"]))

        stream_data = http.json(res, schema=TVPlayer._stream_schema)

        return HLSStream.parse_variant_playlist(self.session,
                                                stream_data["tvplayer"]["response"]["stream"],
                                                headers={'user-agent': TVPlayer._user_agent})


__plugin__ = TVPlayer
