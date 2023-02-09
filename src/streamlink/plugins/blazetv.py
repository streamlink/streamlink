"""
$description British live TV channel and video on-demand service from Blaze, owned by A&E Networks UK.
$url blaze.tv
$type live, vod
$region United Kingdom
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:watch\.)?blaze\.tv/(?:(?P<is_live>live)|watch/replay/\d+)",
))
class BlazeTV(Plugin):
    @staticmethod
    def _get_live_uvid(parsed_html):
        schema = validate.Schema(
            validate.xml_xpath_string(".//div[@id='live-player-root']/@data-player-uvid"),
        )
        return schema.validate(parsed_html)

    @staticmethod
    def _get_vod_uvid(parsed_html):
        schema = validate.Schema(
            validate.xml_xpath_string(".//script[contains(text(), 'window.nowPlaying.setData')]"),
            validate.none_or_all(
                re.compile(r"window\.nowPlaying\.setData\(({.*?})\);"),
                validate.none_or_all(
                    validate.get(1),
                    validate.parse_json(),
                    {
                        "id": str,
                        "series_title": str,
                        "title": str,
                        "season": str,
                        "episode": str,
                    },
                ),
            ),
        )
        return schema.validate(parsed_html)

    def _get_tokenizer(self, streamtype, uvid):
        return self.session.http.get(
            f"https://watch.blaze.tv/stream/{streamtype}/widevine/{uvid}",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "tokenizer": {
                        "url": validate.url(),
                        "uvid": str,
                        "expiry": int,
                        "token": str,
                    },
                },
                validate.get("tokenizer"),
            ),
        )

    def _get_streams(self):
        is_live = self.match.group("is_live")
        parsed_html = self.session.http.get(self.url, schema=validate.Schema(validate.parse_html()))

        if is_live:
            uvid = self._get_live_uvid(parsed_html)
            if not uvid or not uvid.isdecimal():
                return
            token_data = self._get_tokenizer("live", uvid)
            self.id = uvid
            self.author = "Blaze"
            self.title = "Live TV"
            self.category = "Live"
        else:
            data = self._get_vod_uvid(parsed_html)
            if not data or not data["id"] or not data["id"].isdecimal():
                return
            token_data = self._get_tokenizer("replay", data["id"])
            self.id = data["id"]
            self.author = data["series_title"]
            self.title = data["title"]
            self.category = f"S{data['season']}E{data['episode']}"

        log.trace(f"token_data={token_data!r}")

        hls_url = self.session.http.get(
            token_data["url"],
            headers={
                "Token": token_data["token"],
                "Token-Expiry": str(token_data["expiry"]),
                "Uvid": token_data["uvid"],
            },
            schema=validate.Schema(
                validate.parse_json(),
                {"Streams": {"Adaptive": validate.url()}},
                validate.get(("Streams", "Adaptive")),
            ),
        )
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = BlazeTV
