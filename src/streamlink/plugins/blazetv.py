"""
$description British live TV channel and video on-demand service from Blaze, owned by A&E Networks UK.
$url blaze.tv
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
$region United Kingdom
"""

import re

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:(?:www|watch)\.)?blaze\.tv/(?:(?P<is_live>live)|watch/replay/\d+)"),
)
class BlazeTV(Plugin):
    API_URL = "https://v2-streams-elb.simplestreamcdn.com/api/live/stream/{uvid}"

    def _get_live_data(self):
        parsed_html = self.session.http.get(
            self.url,
            schema=validate.Schema(validate.parse_html()),
        )

        schema = validate.Schema(
            validate.xml_xpath(
                ".//*[@data-type='live'][re:test(@data-uvid,'^[0-9]+$')][1]",
                namespaces={"re": "http://exslt.org/regular-expressions"},
            ),
            validate.get(0),
            validate.none_or_all(
                validate.union_get(
                    "data-uvid",
                    "data-key",
                    "data-token",
                    "data-expiry",
                ),
            ),
        )

        return schema.validate(parsed_html)

    def _get_vod_uvid(self):
        parsed_html = self.session.http.get(
            self.url,
            schema=validate.Schema(validate.parse_html()),
        )
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

    def _get_stream(self, uvid, key, token, expiry):
        return self.session.http.post(
            self.API_URL.format(uvid=uvid),
            params={
                "key": key,
                "platform": "chrome",
            },
            headers={
                "Accept": "application/json",
                "Token": token,
                "Token-Expiry": expiry,
                "Userid": "123456",
                "Uvid": uvid,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "response": {
                        "stream": validate.url(),
                    },
                },
                validate.get(("response", "stream")),
            ),
        )

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

    def _get_hls_url(self, token_data):
        return self.session.http.get(
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

    def _get_streams(self):
        is_live = self.match.group("is_live")

        if is_live:
            data = self._get_live_data()
            if not data:
                return

            uvid, key, token, expiry = data

            self.id = uvid
            self.author = "Blaze"
            self.title = "Live TV"
            self.category = "Live"

            hls_url = self._get_stream(
                uvid,
                key,
                token,
                expiry,
            )
        else:
            data = self._get_vod_uvid()
            if not data or not data["id"] or not data["id"].isdecimal():
                return

            token_data = self._get_tokenizer("replay", data["id"])

            self.id = data["id"]
            self.author = data["series_title"]
            self.title = data["title"]
            self.category = f"S{data['season']}E{data['episode']}"

            log.trace("token_data=%r", token_data)

            hls_url = self._get_hls_url(token_data)

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = BlazeTV
