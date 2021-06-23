import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json, parse_qsd
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?mitele\.es/directo/(?P<channel>[\w-]+)"
))
class Mitele(Plugin):
    caronte_url = "https://caronte.mediaset.es/delivery/channel/mmc/{channel}/mtweb"
    gbx_url = "https://mab.mediaset.es/1.0.0/get?oid=mtmw&eid=%2Fapi%2Fmtmw%2Fv2%2Fgbx%2Fmtweb%2Flive%2Fmmc%2F{channel}"

    error_schema = validate.Schema({"code": int})
    caronte_schema = validate.Schema(validate.transform(parse_json), validate.any(
        {
            "cerbero": validate.url(),
            "bbx": str,
            "dls": [{
                "lid": validate.all(int, validate.transform(str)),
                "format": validate.any("hls", "dash", "smooth"),
                "stream": validate.url(),
                validate.optional("assetKey"): str,
                "drm": bool,
            }],
        },
        error_schema,
    ))
    gbx_schema = validate.Schema(
        validate.transform(parse_json),
        {"gbx": str},
        validate.get("gbx")
    )
    cerbero_schema = validate.Schema(
        validate.transform(parse_json),
        validate.any(
            validate.all(
                {"tokens": {str: {"cdn": str}}},
                validate.get("tokens")
            ),
            error_schema,
        )
    )
    token_errors = {
        4038: "User has no privileges"
    }

    def _get_streams(self):
        channel = self.match.group("channel")

        pdata = self.session.http.get(self.caronte_url.format(channel=channel),
                                      acceptable_status=(200, 403, 404),
                                      schema=self.caronte_schema)
        gbx = self.session.http.get(self.gbx_url.format(channel=channel),
                                    schema=self.gbx_schema)

        if "code" in pdata:
            log.error("error getting pdata: {}".format(pdata["code"]))
            return

        tokens = self.session.http.post(pdata["cerbero"],
                                        acceptable_status=(200, 403, 404),
                                        json={"bbx": pdata["bbx"], "gbx": gbx},
                                        headers={"origin": "https://www.mitele.es"},
                                        schema=self.cerbero_schema)

        if "code" in tokens:
            log.error("Could not get stream tokens: {} ({})".format(tokens["code"],
                                                                    self.token_errors.get(tokens["code"], "unknown error")))
            return

        list_urls = []
        for stream in pdata["dls"]:
            if stream["drm"]:
                log.warning("Stream may be protected by DRM")
            else:
                sformat = stream.get("format")
                log.debug("Stream: {} ({})".format(stream["stream"], sformat or "n/a"))
                cdn_token = tokens.get(stream["lid"], {}).get("cdn", "")
                qsd = parse_qsd(cdn_token)
                if sformat == "hls":
                    list_urls.append(update_qsd(stream["stream"], qsd))

        if not list_urls:
            return

        for url in list(set(list_urls)):
            yield from HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}").items()


__plugin__ = Mitele
