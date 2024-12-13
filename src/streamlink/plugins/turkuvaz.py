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
$metadata id
$metadata title
$region various
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="atvavrupa",
    pattern=re.compile(r"https?://(?:www\.)?atvavrupa\.tv"),
)
@pluginmatcher(
    name="ahaber",
    pattern=re.compile(r"https?://(?:www\.)?ahaber\.com\.tr"),
)
@pluginmatcher(
    name="anews",
    pattern=re.compile(r"https?://(?:www\.)?anews\.com\.tr"),
)
@pluginmatcher(
    name="apara",
    pattern=re.compile(r"https?://(?:www\.)?apara\.com\.tr"),
)
@pluginmatcher(
    name="aspor",
    pattern=re.compile(r"https?://(?:www\.)?aspor\.com\.tr"),
)
@pluginmatcher(
    name="atv",
    pattern=re.compile(r"https?://(?:www\.)?atv\.com\.tr"),
)
@pluginmatcher(
    name="minikacocuk",
    pattern=re.compile(r"https?://(?:www\.)?minikacocuk\.com\.tr"),
)
@pluginmatcher(
    name="minikago",
    pattern=re.compile(r"https?://(?:www\.)?minikago\.com\.tr"),
)
@pluginmatcher(
    name="vavtv",
    pattern=re.compile(r"https?://(?:www\.)?vavtv\.com\.tr"),
)
class Turkuvaz(Plugin):
    _VIDEOID_LIVE = "00000000-0000-0000-0000-000000000000"

    # hardcoded in https://i.tmgrup.com.tr/videojs/js/tmdplayersetup.js?v=651
    # (via https://www.minikacocuk.com.tr/webtv/canli-yayin)
    _MAPPING_WEBSITEID_HLSURL = {
        "9BBE055A-4CF6-4BC3-A675-D40E89B55B91": "https://trkvz.daioncdn.net/aspor/aspor.m3u8?ce=3&app=45f847c4-04e8-419a-a561-2ebf87084765",
        "0C1BC8FF-C3B1-45BE-A95B-F7BB9C8B03ED": "https://trkvz.daioncdn.net/a2tv/a2tv.m3u8?ce=3&app=59363a60-be96-4f73-9eff-355d0ff2c758",
        "AAE2E325-4EAE-45B7-B017-26FD7DDB6CE4": "https://trkvz.daioncdn.net/minikago/minikago.m3u8?app=web&ce=3",
        "01ED59F2-4067-4945-8204-45F6C6DB4045": "https://trkvz.daioncdn.net/minikago_cocuk/minikago_cocuk.m3u8?app=web&ce=3",
    }

    def _get_streams(self):
        find_and_get_attrs = validate.all(
            validate.xml_find(".//div[@data-videoid][@data-websiteid]"),
            validate.union_get("data-videoid", "data-websiteid"),
        )

        id_data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.any(
                    find_and_get_attrs,
                    validate.all(
                        validate.xml_xpath_string(
                            ".//script[contains(text(),'data-videoid') and contains(text(),'data-websiteid')]/text()",
                        ),
                        validate.none_or_all(
                            str,
                            validate.regex(re.compile(r"""var\s+tmdPlayer\s*=\s*(?P<q>["'])(.*?)(?P=q)""")),
                            validate.get(0),
                            validate.parse_html(),
                            find_and_get_attrs,
                        ),
                    ),
                ),
            ),
        )

        if not id_data:
            return

        video_id, website_id = id_data
        log.debug(f"{video_id=}")
        log.debug(f"{website_id=}")

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

        if video_id == self._VIDEOID_LIVE:
            hls_url = self._MAPPING_WEBSITEID_HLSURL.get(website_id.upper(), hls_url)
        log.debug(f"{hls_url=}")

        secure_hls_url = self.session.http.get(
            "https://securevideotoken.tmgrup.com.tr/webtv/secure",
            params={"url": hls_url},
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
        log.debug(f"{secure_hls_url=}")

        if secure_hls_url:
            return HLSStream.parse_variant_playlist(self.session, secure_hls_url)


__plugin__ = Turkuvaz
