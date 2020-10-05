import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream
from streamlink.utils import parse_json


class Mbcmini(Plugin):
    _url_re = re.compile(r'https?://miniplay\.imbc\.com/WebLiveURL\.ashx\?channel=(?P<channel_id>[a-z]+)')

    _api_url = 'http://miniplay.imbc.com/WebLiveURL.ashx?channel={0}&protocol=M3U8' \
               '&agent=android&androidversion=18&callback=jarvis.miniInfo.loadOnAirComplete'

    _json_re = re.compile(r'jarvis\.miniInfo\.loadOnAirComplete\(\s*(\{.+\})\s*\)', re.DOTALL)

    _stream_schema = validate.Schema(
        validate.transform(_json_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            validate.get('AACLiveURL'),
            validate.url()
        ))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        match = self._url_re.match(self.url)
        channel_id = match.group('channel_id')

        headers = {
            'User-Agent': useragents.CHROME,
            'Referer': 'http://mini.imbc.com/webapp_v3/minifloat.html'
                       '?src=http://www.imbc.com/broad/radio/minimbc/index.html&ref='
        }
        url = self._api_url.format(channel_id)

        stream_url = self.session.http.get(url, headers=headers, schema=self._stream_schema)

        if stream_url:
            for name, stream in HLSStream.parse_variant_playlist(self.session, stream_url).items():
                yield name, stream


__plugin__ = Mbcmini
