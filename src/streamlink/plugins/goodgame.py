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
from urllib.parse import parse_qsl, urlparse

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:www\.)?goodgame\.ru/(?P<name>(?!channel|player)[^/?]+)",
    ),
)
@pluginmatcher(
    name="channel",
    pattern=re.compile(
        r"https?://(?:www\.)?goodgame\.ru/channel/(?P<channel>[^/?]+)",
    ),
)
@pluginmatcher(
    name="player",
    pattern=re.compile(
        r"https?://(?:www\.)?goodgame\.ru/player\?(?P<id>\d+)$",
    ),
)
class GoodGame(Plugin):
    _API_STREAMS_ID = "https://goodgame.ru/api/4/streams/2/id/{id}"
    _API_STREAMS_CHANNEL = "https://goodgame.ru/api/4/streams/2/channel/{channel}"
    _URL_HLS = "https://hls.goodgame.ru/manifest/{id}_master.m3u8"

    def _get_channel_key(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"api:(?P<json>{.+?}),\n"),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    {"channel_key": str},
                    validate.get("channel_key"),
                ),
            ),
        )

    def _get_api_url(self):
        if self.matches["default"]:
            channel = self._get_channel_key()
            log.debug(f"{channel=}")
            if not channel:
                raise NoStreamsError
            return self._API_STREAMS_CHANNEL.format(channel=channel)

        elif self.matches["channel"]:
            return self._API_STREAMS_CHANNEL.format(channel=self.match["channel"])

        elif self.matches["player"]:
            return self._API_STREAMS_ID.format(id=self.match["id"])

        raise PluginError("Invalid matcher")

    def _api_stream(self, url):
        return self.session.http.get(
            url,
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
                            "streamKey": str,
                            "game": {
                                "title": validate.none_or_all(str),
                            },
                            "title": validate.none_or_all(str),
                            "players": [
                                validate.all(
                                    {
                                        "title": str,
                                        "online": bool,
                                        "content": validate.all(
                                            str,
                                            validate.parse_html(),
                                            validate.xml_find(".//iframe"),
                                            validate.get("src"),
                                            validate.transform(urlparse),
                                        ),
                                    },
                                    validate.union_get(
                                        "title",
                                        "online",
                                        "content",
                                    ),
                                ),
                            ],
                        },
                        validate.union_get(
                            "online",
                            "id",
                            ("streamer", "username"),
                            ("game", "title"),
                            "title",
                            "streamKey",
                            "players",
                        ),
                        validate.transform(lambda data: ("data", *data)),
                    ),
                ),
            ),
        )

    def _get_streams(self):
        api_url = self._get_api_url()
        log.debug(f"{api_url=}")

        result, *data = self._api_stream(api_url)
        if result == "error":
            log.error(data[0] or "Unknown error")
            return

        online, self.id, self.author, self.category, self.title, stream_key, players = data
        hls_url = self._URL_HLS.format(id=stream_key)

        if online and self.session.http.get(hls_url, raise_for_status=False).status_code < 400:
            return HLSStream.parse_variant_playlist(self.session, hls_url)

        log.debug("Channel is offline, checking for embedded players...")
        for p_title, p_online, p_url in players:
            if p_title == "Twitch" and p_online:
                channel = dict(parse_qsl(p_url.query)).get("channel")
                if channel:
                    log.debug(f"Redirecting to Twitch: {channel=}")
                    return self.session.streams(f"twitch.tv/{channel}")


__plugin__ = GoodGame
