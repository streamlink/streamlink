"""
$description Russian live-streaming platform for live video game broadcasts.
$url goodgame.ru
$type live
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re
import sys

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:www\.)?goodgame\.ru/(?P<channel>(?!player)[^/?#]+)",
    ),
)
@pluginmatcher(
    name="player",
    pattern=re.compile(
        r"https?://(?:www\.)?goodgame\.ru/player\?(?P<channel_id>[^&#]+)",
    ),
)
class GoodGame(Plugin):
    _API_PLAYER = "https://goodgame.ru/api/player"
    _API_STREAM = "https://goodgame.ru/api/4/users/{channel}/stream"

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return sys.maxsize, stream
        return super().stream_weight(stream)

    def _get_channel_from_player(self):
        return self.session.http.get(
            self._API_PLAYER,
            params={"src": self.match["channel_id"]},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "streamer_name": str,
                },
                validate.get("streamer_name"),
            ),
        )

    def _api_stream(self, channel):
        return self.session.http.get(
            self._API_STREAM.format(channel=channel),
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "error": str,
                        },
                        validate.get("error"),
                        validate.transform(lambda data: ("error", data)),
                    ),
                    validate.all(
                        {
                            "online": bool,
                            "id": int,
                            "streamer": {
                                "username": str,
                            },
                            "sources": {
                                str: validate.url(),
                            },
                            "gameObj": {
                                "title": validate.none_or_all(str),
                            },
                            "title": validate.none_or_all(str),
                        },
                        validate.union_get(
                            "online",
                            "id",
                            ("streamer", "username"),
                            ("gameObj", "title"),
                            "title",
                            "sources",
                        ),
                        validate.transform(lambda data: ("data", *data)),
                    ),
                ),
            ),
        )

    def _get_streams(self):
        if self.matches["player"]:
            channel = self._get_channel_from_player()
        else:
            channel = self.match["channel"]

        result, *data = self._api_stream(channel)
        if result == "error":
            log.error(data[0] or "Unknown error")
            return

        online, self.id, self.author, self.category, self.title, sources = data

        if not online:
            return

        streams = {}
        for name, hls_url in sources.items():
            if str.isnumeric(name):
                name = f"{name}p"
            elif name != "source":
                continue
            streams[name] = HLSStream(self.session, hls_url)

        return streams


__plugin__ = GoodGame
