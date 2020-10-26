import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Turkuvaz(Plugin):
    """
    Plugin to support ATV/A2TV Live streams from www.atv.com.tr and www.a2tv.com.tr
    """

    _url_re = re.compile(r"""(?x)https?://(?:www\.)?
    (?:
        (?:
            (atvavrupa)\.tv
            |
            (atv|a2tv|ahaber|aspor|minikago|minikacocuk|anews)\.com\.tr
        )/webtv/(?:live-broadcast|canli-yayin)
    |
        sabah\.com\.tr/(apara)/canli-yayin
    )""")
    _hls_url = "https://trkvz-live.ercdn.net/{channel}/{channel}.m3u8"
    _token_url = "https://securevideotoken.tmgrup.com.tr/webtv/secure"
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
        domain = url_m.group(1) or url_m.group(2) or url_m.group(3)
        # remap the domain to channel
        channel = {"atv": "atvhd",
                   "ahaber": "ahaberhd",
                   "apara": "aparahd",
                   "aspor": "asporhd",
                   "anews": "anewshd",
                   "minikacocuk": "minikagococuk"}.get(domain, domain)
        hls_url = self._hls_url.format(channel=channel)
        # get the secure HLS URL
        res = self.session.http.get(self._token_url,
                                    params="url={0}".format(hls_url),
                                    headers={"Referer": self.url,
                                             "User-Agent": useragents.CHROME})

        secure_hls_url = self.session.http.json(res, schema=self._token_schema)

        log.debug("Found HLS URL: {0}".format(secure_hls_url))
        return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = Turkuvaz
