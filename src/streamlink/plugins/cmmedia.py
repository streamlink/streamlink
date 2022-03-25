"""
$description Live TV channel and video on-demand service from CMM, a Spanish public, state-owned broadcaster.
$url cmmedia.es
$type live, vod
$notes Content not licensed for digital distribution is unavailable via the live channel stream.
"""

import logging
import re
from functools import partial

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?cmmedia\.es"))
class CMMedia(Plugin):
    iframe_url_re = re.compile(r'{getKs\("([^"]+)"')
    json_re = re.compile(r"twindow\.kalturaIframePackageData\s*=\s*({.*});[\\nt]*var isIE8")
    unescape_quotes = partial(re.compile(r'\\"').sub, r'"')
    partner_ids_re = re.compile(r"/p/(\d+)/sp/(\d+)/")

    @staticmethod
    def is_restricted(data):
        items = {k: v for k, v in data.items() if k.startswith("is")}
        for k, v in items.items():
            log.debug(f"{k}: {v}")

        restrictions = [k for k, v in items.items() if v]
        if restrictions:
            log.error(f"This site is restricted: ({', '.join(restrictions)})")
            return True

        return False

    def _get_streams(self):
        parsed_html = self.session.http.get(self.url, schema=validate.Schema(validate.parse_html()))

        iframe_url = validate.validate(validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), '/embedIframeJs/')]/text()"),
            validate.any(None, validate.all(
                validate.transform(self.iframe_url_re.search),
                validate.any(None, validate.all(validate.get(1), validate.url())),
            )),
        ), parsed_html)

        if not iframe_url:
            return

        m = self.partner_ids_re.search(iframe_url)
        if not m:
            log.error("Failed to find partner IDs in IFRAME URL")
            return

        p = m.group(1)
        sp = m.group(2)

        json = self.session.http.get(iframe_url, schema=validate.Schema(
            validate.transform(self.json_re.search),
            validate.any(None, validate.all(
                validate.get(1),
                validate.transform(self.unescape_quotes),
                validate.parse_json(),
                validate.any({
                    "entryResult": {
                        "contextData": {
                            "isSiteRestricted": bool,
                            "isCountryRestricted": bool,
                            "isSessionRestricted": bool,
                            "isIpAddressRestricted": bool,
                            "isUserAgentRestricted": bool,
                            "flavorAssets": [{
                                "id": str,
                            }],
                        },
                        "meta": {
                            "id": str,
                            "name": str,
                            "categories": validate.any(None, str),
                        },
                    },
                }, {"error": str}),
            )),
        ))

        if not json:
            return

        if "error" in json:
            log.error(f"API error: {json['error']}")
            return

        json = json.get("entryResult")

        if self.is_restricted(json["contextData"]):
            return

        self.id = json["meta"]["id"]
        self.title = json["meta"]["name"]
        self.author = validate.validate(validate.Schema(
            validate.xml_xpath_string(".//h1[contains(@class, 'btn-title')]/text()"),
        ), parsed_html)
        if json["meta"]["categories"]:
            self.category = json["meta"]["categories"]

        for asset in json["contextData"]["flavorAssets"]:
            yield from HLSStream.parse_variant_playlist(
                self.session, (
                    f"https://cdnapisec.kaltura.com/p/{p}/sp/{sp}/playManifest/entryId/{json['meta']['id']}"
                    f"/flavorIds/{asset['id']}/format/applehttp/protocol/https/a.m3u8"
                ),
                name_fmt="{pixels}_{bitrate}",
            ).items()


__plugin__ = CMMedia
