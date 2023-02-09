"""
$description Global live streaming and video on-demand hosting platform.
$url ott.streann.com
$url centroecuador.ec
$url columnaestilos.com
$url evtv.online/noticias-de-venezuela
$url telecuracao.com
$type live, vod
"""

import base64
import logging
import random
import re
import time
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.crypto import decrypt_openssl
from streamlink.utils.parse import parse_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://ott\.streann\.com/s(?:treaming|-secure)/player\.html",
))
@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?(?:
        centroecuador\.ec
        |
        columnaestilos\.com
        |
        crc\.cr/estaciones/
        |
        evtv\.online/noticias-de-venezuela/
        |
        telecuracao\.com
    )
""", re.VERBOSE))
@pluginargument(
    "url",
    metavar="URL",
    type=str,
    help="Source URL where the iframe is located, only required for direct URLs of ott.streann.com",
)
class Streann(Plugin):
    base_url = "https://ott.streann.com"
    get_time_url = base_url + "/web/services/public/get-server-time"
    token_url = base_url + "/loadbalancer/services/web-players/{playerId}/token/{type}/{dataId}/{deviceId}"
    stream_url = (
        base_url
        + "/loadbalancer/services/web-players/{type}s-reseller-secure/{dataId}/{playerId}"
        + "/{token}/{resellerId}/playlist.m3u8?date={time}&device-type=web&device-name=web"
        + "&device-os=web&device-id={deviceId}"
    )
    passphrase_re = re.compile(r"""CryptoJS\.AES\.decrypt\(.*?,\s*(['"])(?P<passphrase>(?:(?!\1).)*)\1\s*?\);""")

    _device_id = None
    _domain = None

    @property
    def device_id(self):
        """
        Randomly generated deviceId.
        :return:
        """
        if self._device_id is None:
            self._device_id = "".join(
                random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(50))
        return self._device_id

    @property
    def time(self):
        res = self.session.http.get(self.get_time_url)
        data = self.session.http.json(res)
        return str(data.get("serverTime", int(time.time() * 1000)))

    def passphrase(self):
        log.debug("passphrase")
        res = self.session.http.get(self.url)
        passphrase_m = self.passphrase_re.search(res.text)
        return passphrase_m and passphrase_m.group("passphrase").encode("utf8")

    def get_token(self, **config):
        log.debug("get_token")
        pdata = dict(arg1=base64.b64encode(self._domain.encode("utf8")),
                     arg2=base64.b64encode(self.time.encode("utf8")))

        headers = {
            "Referer": self.url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        res = self.session.http.post(
            self.token_url.format(deviceId=self.device_id, **config),
            data=pdata,
            headers=headers,
        )

        if res.status_code == 204:
            log.error(f"self._domain might be invalid - {self._domain}")
            return

        data = self.session.http.json(res, schema=validate.Schema({
            "token": str,
            validate.optional("name"): str,
            validate.optional("webPlayer"): {
                validate.optional("id"): str,
                validate.optional("name"): str,
                validate.optional("type"): str,
                validate.optional("allowedDomains"): [str],
            },
        }))
        log.trace(f"{data!r}")
        self.title = data.get("name")
        return data["token"]

    def _get_streams(self):
        if not self.matches[0]:
            self._domain = urlparse(self.url).netloc
            iframes = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_findall(".//iframe[@src]"),
                validate.filter(lambda elem: urlparse(elem.attrib.get("src")).netloc == "ott.streann.com"),
            ))
            if not iframes:
                log.error("Could not find 'ott.streann.com' iframe")
                return
            self.url = iframes[0].attrib.get("src")

        if not self._domain and self.get_option("url"):
            self._domain = urlparse(self.get_option("url")).netloc

        if self._domain is None:
            log.error("Missing source URL, use --streann-url")
            return

        self.session.http.headers.update({"Referer": self.url})
        # Get the query string
        encrypted_data = urlparse(self.url).query
        data = base64.b64decode(encrypted_data)
        # and decrypt it
        passphrase = self.passphrase()
        if passphrase:
            log.debug("Found passphrase")
            params = decrypt_openssl(data, passphrase)
            config = parse_qsd(params.decode("utf8"))
            log.trace(f"config: {config!r}")
            token = self.get_token(**config)
            if not token:
                return
            hls_url = self.stream_url.format(time=self.time,
                                             deviceId=self.device_id,
                                             token=token,
                                             **config)
            log.debug("URL={0}".format(hls_url))
            return HLSStream.parse_variant_playlist(self.session,
                                                    hls_url,
                                                    acceptable_status=(200, 403, 404, 500))


__plugin__ = Streann
