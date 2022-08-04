"""
$description Chinese live-streaming platform for live video game broadcasts and individual live streams.
$url huajiao.com
$type live
"""

import base64
import random
import re
import time
import uuid

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?huajiao\.com/l/(?P<channel>[^/]+)"
))
class Huajiao(Plugin):
    URL_LAPI = "https://g2.live.360.cn/liveplay"

    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"var\s*feed\s*=\s*(?P<feed>{.+?})\s*;", re.DOTALL),
                validate.none_or_all(
                    validate.get("feed"),
                    validate.parse_json(),
                    {
                        "author": {
                            "nickname": str,
                        },
                        "feed": {
                            "title": str,
                            "game": str,
                            "m3u8": validate.any("", validate.url()),
                            "sn": str,
                        },
                        "relay": {
                            "channel": str,
                        },
                    },
                    validate.union_get(
                        ("author", "nickname"),
                        ("feed", "title"),
                        ("feed", "game"),
                        ("feed", "m3u8"),
                        ("feed", "sn"),
                        ("relay", "channel"),
                    ),
                ),
            ),
        )
        if not data:
            return

        self.author, self.title, self.category, m3u8, sn, channel_sid = data

        if m3u8:
            return HLSStream(self.session, m3u8)

        stream_url = self.session.http.get(
            self.URL_LAPI,
            params={
                "stype": "flv",
                "channel": channel_sid,
                "bid": "huajiao",
                "sn": sn,
                "sid": uuid.uuid4().hex.upper(),
                "_rate": "xd",
                "ts": time.time(),
                "r": random.random(),
            },
            schema=validate.Schema(
                validate.transform(lambda text: base64.b64decode(text[0:3] + text[6:]).decode("utf-8")),
                validate.parse_json(),
                {"main": validate.url()},
                validate.get("main"),
            ),
        )
        return {"live": HTTPStream(self.session, stream_url)}


__plugin__ = Huajiao
