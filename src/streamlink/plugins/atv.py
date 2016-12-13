import random
import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class ATV(Plugin):
    """
    Plugin to support ATV/A2TV Live streams from www.atv.com.tr and www.a2tv.com.tr
    """

    _url_re = re.compile(r"http://www.(a2?tv).com.tr/webtv/canli-yayin")
    _hls_url = "http://trkvz-live.ercdn.net/{channel}/{channel}.m3u8"
    _token_url = "http://videotoken.tmgrup.com.tr/webtv/secure"
    _token_schema = validate.Schema(validate.all(
        {
            "Success": True,
            "Url": validate.url(),
        },
        validate.get("Url"))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        domain = self._url_re.match(self.url).group(1)
        # remap the domain to channel
        channel = {"atv": "atvhd"}.get(domain, domain)

        hls_url = self._hls_url.format(channel=channel)
        # get the secure HLS URL
        res = http.get(self._token_url, params={"url": hls_url})
        secure_hls_url = http.json(res, schema=self._token_schema)

        return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = ATV
