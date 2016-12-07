import random
import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class ATV(Plugin):
    """
    Plugin to support ATV Live stream from http://www.atv.com.tr/webtv/canli-yayin
    """

    _url_re = re.compile(r"http://www.atv.com.tr/webtv/canli-yayin")
    _hls_url = "http://trkvz-live.ercdn.net/atvhd/atvhd.m3u8"
    _token_url = "http://videotoken.tmgrup.com.tr/webtv/secure"
    _token_schema = validate.Schema({
        "Success": True,
        "Url": validate.url(),
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = http.get(self._token_url, params={"url": self._hls_url})
        data = http.json(res, schema=self._token_schema)
        return HLSStream.parse_variant_playlist(self.session, data["Url"])


__plugin__ = ATV
