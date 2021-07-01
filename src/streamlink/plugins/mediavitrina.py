import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?P<channel>ctc(?:love)?|chetv|domashniy|5-tv)\.ru/(?:online|live)"
))
@pluginmatcher(re.compile(
    r"https?://(?P<channel>ren)\.tv/live"
))
@pluginmatcher(re.compile(
    r"https?://player\.mediavitrina\.ru/(?P<channel>[^/?]+.)(?:/[^/]+)?/\w+/player\.html"
))
class MediaVitrina(Plugin):
    def _get_streams(self):
        channel = self.match.group("channel")
        channels = [
            # ((channels), (path, channel))
            (("5-tv", "tv-5", "5tv"), ("tv5", "tv-5")),
            (("chetv", "ctc-che", "che_ext"), ("ctc", "ctc-che")),
            (("ctc"), ("ctc", "ctc")),
            (("ctclove", "ctc-love", "ctc_love_ext"), ("ctc", "ctc-love")),
            (("domashniy", "ctc-dom", "domashniy_ext"), ("ctc", "ctc-dom")),
            (("iz"), ("iz", "iz")),
            (("mir"), ("mtrkmir", "mir")),
            (("muztv"), ("muztv", "muztv")),
            (("ren", "ren-tv", "rentv"), ("nmg", "ren-tv")),
            (("russia1"), ("vgtrk", "russia1")),
            (("russia24"), ("vgtrk", "russia24")),
            (("russiak", "kultura"), ("vgtrk", "russiak")),
            (("spas"), ("spas", "spas")),
            (("tvc"), ("tvc", "tvc")),
            (("tvzvezda", "zvezda"), ("zvezda", "zvezda")),
            (("u", "u_ott"), ("utv", "u_ott")),
        ]
        for c in channels:
            if channel in c[0]:
                path, channel = c[1]
                break
        else:
            log.error("Unsupported channel: {0}".format(channel))
            return

        res_token = self.session.http.get(
            "https://media.mediavitrina.ru/get_token",
            schema=validate.Schema(
                validate.transform(parse_json),
                {"result": {"token": validate.text}},
                validate.get("result"),
            ),
        )
        url = self.session.http.get(
            update_qsd(
                "https://media.mediavitrina.ru/api/v2/{0}/playlist/{1}_as_array.json".format(path, channel), qsd=res_token
            ),
            schema=validate.Schema(
                validate.transform(parse_json),
                {"hls": [validate.url()]},
                validate.get("hls"),
                validate.get(0),
            ),
        )

        if not url:
            return

        if "georestrictions" in url:
            log.error("Stream is geo-restricted")
            return

        for s in HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}").items():
            yield s


__plugin__ = MediaVitrina
