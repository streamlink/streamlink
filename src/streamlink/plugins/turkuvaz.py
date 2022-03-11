"""
$description Turkish live TV channels from Turkuvaz Media Group, including Ahaber, ATV, Minika COCUK and MinikaGO.
$url atv.com.tr
$url a2tv.com.tr
$url ahaber.com.tr
$url anews.com.tr
$url aspor.com.tr
$url atvavrupa.tv
$url minikacocuk.com.tr
$url minikago.com.tr
$url sabah.com.tr
$type live
$region various
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""https?://(?:www\.)?
    (?:
        (?:
            (atvavrupa)\.tv
            |
            (atv|a2tv|ahaber|aspor|minikago|minikacocuk|anews)\.com\.tr
        )/webtv/(?:live-broadcast|canli-yayin)
        |
        (ahaber)\.com\.tr/video/canli-yayin
        |
        atv\.com\.tr/(a2tv)/canli-yayin
        |
        sabah\.com\.tr/(apara)/canli-yayin
    )
""", re.VERBOSE))
class Turkuvaz(Plugin):
    _hls_url = "https://trkvz-live.ercdn.net/{channel}/{channel}.m3u8"
    _token_url = "https://securevideotoken.tmgrup.com.tr/webtv/secure"
    _token_schema = validate.Schema(validate.all(
        {
            "Success": True,
            "Url": validate.url(),
        },
        validate.get("Url"))
    )

    def _get_streams(self):
        url_m = self.match
        domain = url_m.group(1) or url_m.group(2) or url_m.group(3) or url_m.group(4) or url_m.group(5)
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
