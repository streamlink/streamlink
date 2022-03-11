"""
$description TV network with multiple live TV channels broadcasting across various Latin American countries.
$url antena7.com.do
$url atv.pe
$url c9n.com.py
$url canal10.com.ni
$url canal12.com.sv
$url chapintv.com
$url elnueve.com.ar
$url redbolivision.tv.bo
$url repretel.com
$url rts.com.ec
$url snt.com.py
$url tvc.com.ec
$url vtv.com.hn
$type live
$region various
"""

import logging
import re
import time

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (
        antena7\.com\.do
        |
        atv\.pe
        |
        c9n\.com\.py
        |
        canal10\.com\.ni
        |
        canal12\.com\.sv
        |
        chapintv\.com
        |
        elnueve\.com\.ar
        |
        redbolivision\.tv\.bo
        |
        repretel\.com
        |
        rts\.com\.ec
        |
        snt\.com\.py
        |
        tvc\.com\.ec
        |
        vtv\.com\.hn
    )
    /
    (?:
        (?:
            en-?vivo(?:-atv(?:mas)?|-canal-?\d{1,2})?
        )
        |
        upptv
    )
    (?:/|\#)?$
""", re.VERBOSE))
class Albavision(Plugin):
    def __init__(self, url):
        super().__init__(url)
        self._page = None

    @property
    def page(self):
        if self._page is None:
            self._page = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
            ))
        return self._page

    def _is_token_based_site(self):
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'jQuery.get')]/text()"),
        )
        is_token_based_site = validate.validate(schema, self.page) is not None
        log.debug(f"is_token_based_site={is_token_based_site}")
        return is_token_based_site

    def _get_live_url(self):
        live_url_re = re.compile(r"""LIVE_URL\s*=\s*['"]([^'"]+)['"]""")
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'LIVE_URL')]/text()"),
            validate.any(None, validate.all(
                validate.transform(live_url_re.search),
                validate.any(None, validate.all(
                    validate.get(1),
                    validate.url(),
                )),
            )),
        )
        live_url = validate.validate(schema, self.page)
        log.debug(f"live_url={live_url}")
        return live_url

    def _get_token_req_url(self):
        token_req_host_re = re.compile(r"""jQuery\.get\s*\(['"]([^'"]+)['"]""")
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'LIVE_URL')]/text()"),
            validate.any(None, validate.all(
                validate.transform(token_req_host_re.search),
                validate.any(None, validate.all(
                    validate.get(1),
                    validate.url(),
                )),
            )),
        )
        token_req_host = validate.validate(schema, self.page)
        log.debug(f"token_req_host={token_req_host}")

        token_req_str_re = re.compile(r"""Math\.floor\(Date\.now\(\)\s*/\s*3600000\),\s*['"]([^'"]+)['"]""")
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'LIVE_URL')]/text()"),
            validate.any(None, validate.all(
                validate.transform(token_req_str_re.search),
                validate.any(None, validate.all(
                    validate.get(1),
                    str,
                )),
            )),
        )
        token_req_str = validate.validate(schema, self.page)
        log.debug(f"token_req_str={token_req_str}")
        if not token_req_str:
            return

        date = int(time.time() // 3600)
        token_req_token = self.transform_token(token_req_str, date) or self.transform_token(token_req_str, date - 1)

        if token_req_host and token_req_token:
            return update_qsd(token_req_host, {"rsk": token_req_token})

    def _get_token(self):
        token_req_url = self._get_token_req_url()
        if not token_req_url:
            return

        res = self.session.http.get(token_req_url, schema=validate.Schema(
            validate.parse_json(), {
                "success": bool,
                validate.optional("error"): int,
                validate.optional("token"): str,
            },
        ))

        if not res["success"]:
            if res["error"]:
                log.error(f"Token request failed with error: {res['error']}")
            else:
                log.error("Token request failed")
            return

        if not res["token"]:
            log.error("Token not found in response")
            return
        token = res["token"]
        log.debug(f"token={token}")
        return token

    @staticmethod
    def transform_token(token_in, date):
        token_out = list(token_in)
        offset = len(token_in)
        for i in range(offset - 1, -1, -1):
            p = (i * date) % offset
            # swap chars at p and i
            token_out[i], token_out[p] = token_out[p], token_out[i]
        token_out = ''.join(token_out)
        if token_out.endswith("OK"):
            return token_out[:-2]
        else:
            log.error(f"Invalid site token: {token_in} => {token_out}")

    def _get_streams(self):
        live_url = self._get_live_url()
        if not live_url:
            log.info("This stream may be off-air or not available in your country")
            return

        if self._is_token_based_site():
            token = self._get_token()
            if not token:
                return
            return HLSStream.parse_variant_playlist(self.session, update_qsd(live_url, {"iut": token}))
        else:
            return HLSStream.parse_variant_playlist(self.session, live_url)


__plugin__ = Albavision
