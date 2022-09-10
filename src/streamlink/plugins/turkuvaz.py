"""
$description Turkish live TV channels from Turkuvaz Media Group, including Ahaber, ATV, Minika COCUK and MinikaGO.
$url a2tv.com.tr
$url ahaber.com.tr
$url anews.com.tr
$url apara.com.tr
$url aspor.com.tr
$url atv.com.tr
$url atvavrupa.tv
$url minikacocuk.com.tr
$url minikago.com.tr
$url vavtv.com.tr
$type live
$region various
"""

import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        (?:
            atvavrupa\.tv
            |
            (?:atv|a2tv|ahaber|aspor|minikago|minikacocuk|anews)\.com\.tr
        )/webtv/(?:live-broadcast|canli-yayin)
        |
        ahaber\.com\.tr/video/canli-yayin
        |
        (?:apara|vavtv)\.com\.tr/canli-yayin
        |
        atv\.com\.tr/a2tv/canli-yayin
    )
""", re.VERBOSE))
class Turkuvaz(Plugin):
    _URL_HLS = "https://trkvz-live.ercdn.net/{channel}/{channel}.m3u8"
    _URL_TOKEN = "https://securevideotoken.tmgrup.com.tr/webtv/secure"

    _MAP_HOST_TO_CHANNEL = {
        "atv": "atvhd",
        "ahaber": "ahaberhd",
        "apara": "aparahd",
        "aspor": "asporhd",
        "anews": "anewshd",
        "vavtv": "vavtv",
        "minikacocuk": "minikagococuk",
    }

    def _get_streams(self):
        hostname = re.sub(r"^www\.", "", urlparse(self.url).netloc).split(".")[0]

        # remap the domain to channel
        channel = self._MAP_HOST_TO_CHANNEL.get(hostname, hostname)
        hls_url = self._URL_HLS.format(channel=channel)

        # get the secure HLS URL
        secure_hls_url = self.session.http.get(
            self._URL_TOKEN,
            params=f"url={hls_url}",
            headers={"Referer": self.url},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "Success": True,
                    "Url": validate.url(),
                },
                validate.get("Url"),
            ),
        )

        if secure_hls_url:
            return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = Turkuvaz
