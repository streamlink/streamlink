# -*- coding: utf-8 -*-

import re
import requests

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents

YOUTUBE_URL = "https://www.youtube.com/watch?v={0}"
req = requests.get('http://extreme-ip-lookup.com/json/', params={'User-Agent': useragents.CHROME})
j_son = req.json()

_youtube_id = re.compile(r'/embed/([\w-]+)(?:.+?/embed/([\w-]+)|)', re.M | re.S)

_url_re = re.compile(r'http(s)?://webtv\.ert\.gr/ert.+?/')


class Ert(Plugin):

    @classmethod
    def can_handle_url(cls, url):

        return _url_re.match(url)

    def _yt_id(self):

        r1 = requests.get(self.url, params={'User-Agent': useragents.CHROME})

        iframe_url = re.search(r'iframe src="(.+?)"', r1.content, re.U).group(1)

        return iframe_url

    def _youtube_url_schema(self, link):

        _youtube_url_schema = validate.Schema(
            validate.all(
                validate.transform(_youtube_id.search),
                validate.any(
                    None,
                    validate.all(
                        validate.get(
                            2 if j_son['countryCode'] == 'GR' and 'ertworld-live' not in link else 1
                        ),
                        validate.text
                    )
                )
            )
        )

        return _youtube_url_schema

    def _get_streams(self):

        channel_id = http.get(self._yt_id(), schema=self._youtube_url_schema(self.url))

        if channel_id:
            return self.session.streams(YOUTUBE_URL.format(channel_id))


__plugin__ = Ert
