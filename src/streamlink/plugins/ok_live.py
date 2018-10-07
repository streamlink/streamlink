import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

_url_re = re.compile(r"https?://(www\.)?ok\.ru/(live|video)/\d+")
_vod_re = re.compile(r";(?P<hlsurl>[^;]+video\.m3u8.+?)\\&quot;")

_schema = validate.Schema(
    validate.transform(_vod_re.search),
    validate.any(
        None,
        validate.all(
            validate.get("hlsurl"),
            validate.url()
        )
    )
)

class OK_live(Plugin):
    """
    Support for ok.ru live stream: http://www.ok.ru/live/ and for ok.ru VoDs: http://www.ok.ru/video/
    """
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    def _get_streams(self):
        headers = {
            'User-Agent': useragents.CHROME,
            'Referer': self.url
        }

        hls  = self.session.http.get(self.url, headers=headers, schema=_schema)
        if hls:
            hls = hls.replace(u'\\\\u0026', u'&')
        return HLSStream.parse_variant_playlist(self.session, hls, headers=headers)


__plugin__ = OK_live