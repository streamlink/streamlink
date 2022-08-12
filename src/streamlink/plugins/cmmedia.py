"""
$description Live TV channel and video on-demand service from CMM, a Spanish public, state-owned broadcaster.
$url cmmedia.es
$type live, vod
$notes Content not licensed for digital distribution is unavailable via the live channel stream.
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?cmmedia\.es"))
class CMMedia(Plugin):
    @staticmethod
    def is_restricted(data):
        items = {k: v for k, v in data.items() if k.startswith("is")}
        for k, v in items.items():
            log.debug("{0}: {1}".format(k, v))

        restrictions = [k for k, v in items.items() if v]
        if restrictions:
            log.error("This site is restricted: ({0})".format(", ".join(restrictions)))
            return True

        return False

    def _get_streams(self):
        self.author, iframe_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.union((
                validate.xml_xpath_string(".//h1[contains(@class, 'btn-title')]/text()"),
                validate.all(
                    validate.xml_xpath_string(".//script[contains(text(), '/embedIframeJs/')]/text()"),
                    validate.none_or_all(
                        re.compile(r"""{getKs\((?P<q>")(?P<url>.+?)(?P=q)"""),
                        validate.none_or_all(validate.get("url"), validate.url()),
                    ),
                ),
            )),
        ))
        if not iframe_url:
            return

        m = re.search(r"/p/(\d+)/sp/(\d+)/", iframe_url)
        if not m:
            log.error("Failed to find partner IDs in IFRAME URL")
            return

        p = m.group(1)
        sp = m.group(2)

        json = self.session.http.get(iframe_url, schema=validate.Schema(
            re.compile(r"twindow\.kalturaIframePackageData\s*=\s*({.*});[\\nt]*var isIE8"),
            validate.none_or_all(
                validate.get(1),
                validate.transform(lambda text: re.sub(r'\\"', r'"', text)),
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
                                "id": validate.text,
                            }],
                        },
                        "meta": {
                            "id": validate.text,
                            "name": validate.text,
                            "categories": validate.any(None, validate.text),
                        },
                    },
                }, {"error": validate.text}),
            ),
        ))

        if not json:
            return

        if "error" in json:
            log.error("API error: {0}".format(json["error"]))
            return

        json = json.get("entryResult")

        if self.is_restricted(json["contextData"]):
            return

        self.id = json["meta"]["id"]
        self.title = json["meta"]["name"]
        self.category = json["meta"]["categories"]

        for asset in json["contextData"]["flavorAssets"]:
            for s in HLSStream.parse_variant_playlist(
                self.session,
                (
                    "https://cdnapisec.kaltura.com/p/{0}/sp/{1}/playManifest/entryId/{2}"
                    "/flavorIds/{3}/format/applehttp/protocol/https/a.m3u8"
                ).format(p, sp, json['meta']['id'], asset['id']),
                name_fmt="{pixels}_{bitrate}",
            ).items():
                yield s


__plugin__ = CMMedia
