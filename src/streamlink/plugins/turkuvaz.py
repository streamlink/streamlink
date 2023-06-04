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
$type live, vod
$region various
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        atvavrupa\.tv
        |
        (?:a2tv|ahaber|anews|apara|aspor|atv|minikacocuk|minikago|vavtv)\.com\.tr
    )
""", re.VERBOSE))
class Turkuvaz(Plugin):
    def _get_streams(self):
        _find_and_get_attrs = validate.Schema(
            validate.xml_find(".//div[@data-videoid][@data-websiteid]"),
            validate.union_get("data-videoid", "data-websiteid"),
        )

        id_data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.any(
                    _find_and_get_attrs,
                    validate.all(
                        validate.xml_xpath_string(
                            ".//script[contains(text(),'data-videoid') and contains(text(),'data-websiteid')]/text()",
                        ),
                        validate.none_or_all(
                            str,
                            validate.regex(re.compile(r"""var\s+tmdPlayer\s*=\s*(?P<q>["'])(.*?)(?P=q)""")),
                            validate.get(0),
                            validate.parse_html(),
                            _find_and_get_attrs,
                        ),
                    ),
                ),
            ),
        )

        if not id_data:
            return

        video_id, website_id = id_data
        log.debug(f"video_id={video_id}")
        log.debug(f"website_id={website_id}")

        self.id, self.title, hls_url = self.session.http.get(
            f"https://videojs.tmgrup.com.tr/getvideo/{website_id}/{video_id}",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": True,
                    "video": {
                        "VideoId": str,
                        "Title": str,
                        "VideoSmilUrl": validate.url(),
                    },
                },
                validate.get("video"),
                validate.union_get("VideoId", "Title", "VideoSmilUrl"),
            ),
        )
        log.debug(f"hls_url={hls_url}")

        secure_hls_url = self.session.http.get(
            "https://securevideotoken.tmgrup.com.tr/webtv/secure",
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
        log.debug(f"secure_hls_url={secure_hls_url}")

        if secure_hls_url:
            return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = Turkuvaz
