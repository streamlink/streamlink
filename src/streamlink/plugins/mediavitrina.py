"""
$description Russian live streaming platform hosting various Russian live TV channels.
$url mediavitrina.ru
$type live
$region Russia
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""https?://(?:www\.)?(?:
    chetv
    |
    ctc(?:love)?
    |
    domashniy
)\.ru/(?:live|online)""", re.VERBOSE))
@pluginmatcher(re.compile(r"https?://player\.mediavitrina\.ru/.+/player\.html"))
class MediaVitrina(Plugin):
    _re_url_json = re.compile(r"https://media\.mediavitrina\.ru/(?:proxy)?api/v3/[\w-]+/playlist/[\w-]+_as_array\.json[^\"']+")

    def _get_streams(self):
        self.session.http.headers.update({"Referer": self.url})

        p_netloc = urlparse(self.url).netloc
        if p_netloc == "player.mediavitrina.ru":
            # https://player.mediavitrina.ru/
            url_player = self.url
        elif p_netloc.endswith("ctc.ru"):
            # https://ctc.ru/online/
            url_player = self.session.http.get(
                "https://ctc.ru/api/page/v1/online/",
                schema=validate.Schema(
                    validate.parse_json(),
                    {"content": validate.all(
                        [dict],
                        validate.filter(lambda n: n.get("type") == "on-air"),
                        [{"onAirLink": validate.url(netloc="player.mediavitrina.ru")}],
                        validate.get((0, "onAirLink")),
                    )},
                    validate.get("content"),
                ),
            )
        else:
            # https://chetv.ru/online/
            # https://ctclove.ru/online/
            # https://domashniy.ru/online/
            url_player = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//iframe[starts-with(@src,'https://player.mediavitrina.ru/')]/@src"),
            ), acceptable_status=(200, 403, 404))

        if not url_player:
            return

        log.debug(f"url_player={url_player}")
        script_data = self.session.http.get(url_player, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(),'media.mediavitrina.ru/')]/text()"),
        ))
        if not script_data:
            log.debug("invalid script_data")
            return

        m = self._re_url_json.search(script_data)
        if not m:
            log.debug("invalid url_json")
            return

        url_json = m.group(0)
        log.debug(f"url_json={url_json}")
        url_json = re.sub(r"\{\{PLAYER_REFERER_HOSTNAME\}\}", "mediavitrina.ru", url_json)
        url_json = re.sub(r"\{\{[A-Za-z_]+\}\}", "", url_json)

        res_token = self.session.http.get(
            "https://media.mediavitrina.ru/get_token",
            schema=validate.Schema(
                validate.parse_json(),
                {"result": {"token": str}},
                validate.get("result"),
            ))
        url = self.session.http.get(
            update_qsd(url_json, qsd=res_token),
            schema=validate.Schema(
                validate.parse_json(),
                {"hls": [validate.url()]},
                validate.get(("hls", 0)),
            ))

        if not url:
            return

        if "georestrictions" in url:
            log.error("Stream is geo-restricted")
            return

        return HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}")


__plugin__ = MediaVitrina
