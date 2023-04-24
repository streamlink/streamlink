"""
$description Spanish live TV channels from Mediaset Group, including Boing, Cuatro, Divinity, Energy, FDF and Telecinco.
$url mitele.es
$type live
$region Spain
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.parse import parse_qsd
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?mitele\.es/directo/(?P<channel>[\w-]+)",
))
class Mitele(Plugin):
    URL_CARONTE = "https://caronte.mediaset.es/delivery/channel/mmc/{channel}/mtweb"
    URL_GBX = "https://mab.mediaset.es/1.0.0/get"

    TOKEN_ERRORS = {
        4038: "User has no privileges",
    }

    def _get_streams(self):
        channel = self.match.group("channel")

        pdata = self.session.http.get(
            self.URL_CARONTE.format(channel=channel),
            acceptable_status=(200, 403, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"code": int},
                    {
                        "cerbero": validate.url(),
                        "bbx": str,
                        "dls": validate.all(
                            [{
                                "drm": bool,
                                "format": str,
                                "stream": validate.all(
                                    validate.transform(str.strip),
                                    validate.url(),
                                ),
                                "lid": validate.all(
                                    int,
                                    validate.transform(str),
                                ),
                                validate.optional("assetKey"): str,
                            }],
                            validate.filter(lambda obj: obj["format"] == "hls"),
                        ),
                    },
                ),
            ),
        )
        if "code" in pdata:
            log.error(f"Error getting pdata: {pdata['code']}")
            return

        gbx = self.session.http.get(
            self.URL_GBX,
            params={
                "oid": "mtmw",
                "eid": f"/api/mtmw/v2/gbx/mtweb/live/mmc/{channel}",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {"gbx": str},
                validate.get("gbx"),
            ),
        )

        tokens = self.session.http.post(
            pdata["cerbero"],
            acceptable_status=(200, 403, 404),
            json={
                "bbx": pdata["bbx"],
                "gbx": gbx,
            },
            headers={"origin": "https://www.mitele.es"},
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"code": int},
                    validate.all(
                        {"tokens": {str: {"cdn": str}}},
                        validate.get("tokens"),
                    ),
                ),
            ),
        )
        if "code" in tokens:
            tokenerrors = self.TOKEN_ERRORS.get(tokens["code"], "unknown error")
            log.error(f"Could not get stream tokens: {tokens['code']} ({tokenerrors})")
            return

        urls = set()
        for stream in pdata["dls"]:
            if stream["drm"]:
                log.warning("Stream may be protected by DRM")
                continue
            cdn_token = tokens.get(stream["lid"], {}).get("cdn", "")
            qsd = parse_qsd(cdn_token)
            urls.add(update_qsd(stream["stream"], qsd, quote_via=lambda string, *_, **__: string))

        for url in urls:
            yield from HLSStream.parse_variant_playlist(
                self.session,
                url,
                headers={"Origin": "https://www.mitele.es"},
                name_fmt="{pixels}_{bitrate}",
            ).items()


__plugin__ = Mitele
