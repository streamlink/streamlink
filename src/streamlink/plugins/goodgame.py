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
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?goodgame\.ru/(?:channel/)?(?P<user>[^/]+)",
))
class GoodGame(Plugin):
    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return sys.maxsize, stream
        return super().stream_weight(stream)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `/channel/user` returns different JSON data with less useful information
        url = urlparse(self.url)
        self.url = urlunparse(url._replace(path=re.sub(r"^/channel/", "/", url.path)))

    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'channel:{')][1]/text()"),
                re.compile(r"channel:(?P<json>{.+?}),?\n"),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    {
                        "status": bool,
                        "id": int,
                        "streamer": {"username": str},
                        "game": str,
                        "title": str,
                        "sources": validate.all(
                            {str: validate.url()},
                            validate.filter(lambda k, v: ".m3u8" in v),
                        ),
                    },
                    validate.union_get(
                        "status",
                        "id",
                        ("streamer", "username"),
                        "game",
                        "title",
                        "sources",
                    ),
                ),
            ),
        )

        if not data:
            log.error("Could not find channel info")
            return

        status, self.id, self.author, self.category, self.title, sources = data

        if not status:
            log.debug("Channel appears to be offline")
            return

        for name, url in sources.items():
            name = f"{name}{'p' if name.isnumeric() else ''}"
            yield name, HLSStream(self.session, url)


__plugin__ = GoodGame
