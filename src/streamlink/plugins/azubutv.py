#!/usr/bin/env python
import json
import requests

import re

from io import BytesIO
from time import sleep

from streamlink.exceptions import PluginError

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream


HTTP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36"),
    'Accept': 'application/json;pk=BCpkADawqM1gvI0oGWg8dxQHlgT8HkdE2LnAlWAZkOlznO39bSZX726u4JqnDsK3MDXcO01JxXK2tZtJbgQChxgaFzEVdHRjaDoxaOu8hHOO8NYhwdxw9BzvgkvLUlpbDNUuDoc4E4wxDToV'

}

_url_re = re.compile("http(s)?://(\w+\.)?azubu.tv/(?P<domain>\w+)")

PARAMS_REGEX = r"(\w+)=({.+?}|\[.+?\]|\(.+?\)|'(?:[^'\\]|\\')*'|\"(?:[^\"\\]|\\\")*\"|\S+)"
stream_video_url = "http://api.azubu.tv/public/channel/{}/player"


class AzubuTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            weight = 1080
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, "azubutv"

    def _parse_params(self, params):
        rval = {}
        matches = re.findall(PARAMS_REGEX, params)

        for key, value in matches:
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass

            rval[key] = value

        return rval

    def _get_stream_url(self, o):

        match = _url_re.match(self.url);
        channel = match.group('domain');

        channel_info = requests.get(stream_video_url.format(channel))
        j = json.loads(channel_info.text)

        if j["data"]["is_live"] != True:
            return "", False
        else:
            is_live = True

        stream_url = 'https://edge.api.brightcove.com/playback/v1/accounts/3361910549001/videos/ref:{0}'

        r = requests.get(stream_url.format(j["data"]["stream_video"]["reference_id"]), headers=HTTP_HEADERS)
        t = json.loads(r.text)

        stream_url = t["sources"][0]["src"]
        return stream_url, is_live


    def _get_streams(self):
        hls_url, is_live = self._get_stream_url(self)

        if not is_live:
            return

        split = self.url.split(" ")
        params = (" ").join(split[1:])
        params = self._parse_params(params)

        try:
            streams = HLSStream.parse_variant_playlist(self.session, hls_url, **params)
        except IOError as err:
            raise PluginError(err)

        return streams

__plugin__ = AzubuTV