import random
import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class Turkuvaz(Plugin):
    """
    Plugin to support ATV/A2TV Live streams from www.atv.com.tr and www.a2tv.com.tr
    """

    _url_re = re.compile(r"""https?://(?:www.)?
            (?:
                (atv|a2tv|ahaber|aspor|minikago|minikacocuk).com.tr/webtv/canli-yayin|
                (atvavrupa).tv/webtv/videoizle/atv_avrupa/canli_yayin
            )""", re.VERBOSE)
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
        url_m = self._url_re.match(self.url)
        domain = url_m.group(1) or url_m.group(2)
        # remap the domain to channel
        channel = {"atv": "atvhd",
                   "ahaber": "ahaberhd",
                   "aspor": "asporhd"}.get(domain, domain)

        hls_url = self._hls_url.format(channel=channel)
        # get the secure HLS URL
        res = http.get(self._token_url,
                       params={"url": hls_url},
                       headers={"Referer": self.url})
        secure_hls_url = http.json(res, schema=self._token_schema)

        return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = Turkuvaz
