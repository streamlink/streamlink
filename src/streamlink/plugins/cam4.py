import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream, RTMPStream
from streamlink.utils import parse_json


class Cam4(Plugin):
    _url_re = re.compile(r'https?://([a-z]+\.)?cam4.com/.+')
    _video_data_re = re.compile(r"flashData: (?P<flash_data>{.*}), hlsUrl: '(?P<hls_url>.+?)'")

    _flash_data_schema = validate.Schema(
        validate.all(
            validate.transform(parse_json),
            validate.Schema({
                'playerUrl': validate.url(),
                'flashVars': validate.Schema({
                    'videoPlayUrl': validate.text,
                    'videoAppUrl': validate.url(scheme='rtmp')
                })
            })
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return Cam4._url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, headers={'User-Agent': useragents.ANDROID})
        match = self._video_data_re.search(res.text)
        if match is None:
            return

        hls_streams = HLSStream.parse_variant_playlist(
            self.session,
            match.group('hls_url'),
            headers={'Referer': self.url}
        )
        for s in hls_streams.items():
            yield s

        rtmp_video = self._flash_data_schema.validate(match.group('flash_data'))
        rtmp_stream = RTMPStream(self.session, {
            'rtmp': rtmp_video['flashVars']['videoAppUrl'],
            'playpath': rtmp_video['flashVars']['videoPlayUrl'],
            'swfUrl': rtmp_video['playerUrl']
        })
        yield 'live', rtmp_stream


__plugin__ = Cam4
