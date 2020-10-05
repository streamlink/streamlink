# -*- coding: utf-8 -*-
import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Mbcmini(Plugin):

    _url_re = re.compile(r'https?://miniplay\.imbc\.com/WebLiveURL\.ashx\?channel=(?P<channel_id>[a-z]+)')

    _api_url = '''http://miniplay.imbc.com/WebLiveURL.ashx?channel={0}&protocol=M3U8\
&agent=android&androidversion=18&callback=jarvis.miniInfo.loadOnAirComplete'''

    _json_re = re.compile(r'jarvis\.miniInfo\.loadOnAirComplete\(({.*?})', re.DOTALL)

    _stream_schema = validate.Schema(
        validate.transform(_json_re.search),
        validate.all(
            validate.get(1),
            validate.transform(lambda v: v.replace("\n", "")),
            validate.transform(lambda v: v.replace("\t", "")),
            validate.transform(parse_json),
            {
                "AACLiveURL":
                validate.url()
            }, validate.get("AACLiveURL"),
        )
    )

    @ classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        channel_id = match.group("channel_id")

        headers = {
            'User-Agent': useragents.CHROME,
            'Referer': '''http://mini.imbc.com/webapp_v3/minifloat.html?\
src=http://www.imbc.com/broad/radio/minimbc/index.html&ref='''
        }
        url = self._api_url.format(channel_id)

        stream_url = self.session.http.get(url, headers=headers, schema=self._stream_schema)

        if stream_url:
            yield "live", HTTPStream(self.session, stream_url)


__plugin__ = Mbcmini
