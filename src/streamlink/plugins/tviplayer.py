"""
$description Live TV channels and video on-demand service from TVI, a Portuguese free-to-air broadcaster.
$url tviplayer.iol.pt
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https://tviplayer\.iol\.pt/(?:direto|programa)/",
))
class TVIPlayer(Plugin):
    def _get_streams(self):
        self.session.http.headers.update({"Referer": "https://tviplayer.iol.pt/"})
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'.m3u8')]/text()"),
                validate.none_or_all(
                    re.compile(r"jsonData\s*=\s*(?P<json>{.+?})\s*;", re.DOTALL),
                    validate.none_or_all(
                        validate.get("json"),
                        validate.parse_json(),
                        {
                            "id": str,
                            "liveType": str,
                            "videoType": str,
                            "videoUrl": validate.url(path=validate.endswith(".m3u8")),
                            validate.optional("channel"): str,
                        },
                    ),
                ),
            ),
        )
        if not data:
            return
        log.debug(f"{data!r}")

        if data["liveType"].upper() == "DIRETO" and data["videoType"].upper() == "LIVE":
            geo_path = "live"
        else:
            geo_path = "vod"
        data_geo = self.session.http.get(
            f"https://services.iol.pt/direitos/rights/{geo_path}?id={data['id']}",
            acceptable_status=(200, 403),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "code": str,
                    "error": validate.any(None, str),
                    "detail": str,
                },
            ),
        )
        log.debug(f"{data_geo!r}")
        if data_geo["detail"] != "ok":
            log.error(f"{data_geo['detail']}")
            return

        wmsAuthSign = self.session.http.get(
            "https://services.iol.pt/matrix?userId=",
            schema=validate.Schema(str),
        )
        hls_url = update_qsd(data["videoUrl"], {"wmsAuthSign": wmsAuthSign})
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TVIPlayer
