"""
$description TikTok is a short-form video hosting service owned by ByteDance.
$url www.tiktok.com
$type live
$metadata id
$metadata author
$metadata title
"""

from __future__ import annotations

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/?]+)",
    ),
)
class TikTok(Plugin):
    QUALITY_WEIGHTS: dict[str, int] = {}

    _URL_WEB_LIVE = "https://www.tiktok.com/@{channel}/live"
    _URL_API_LIVE_DETAIL = "https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"
    _URL_WEBCAST_ROOM_INFO = "https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room_id}"

    _STATUS_OFFLINE = 4

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, key

        return super().stream_weight(key)

    def _get_streams(self):
        self.id = self.session.http.get(
            self._URL_WEB_LIVE.format(channel=self.match["channel"]),
            allow_redirects=False,
            schema=validate.Schema(
                validate.parse_html(),
                validate.any(
                    validate.all(
                        validate.xml_xpath_string(
                            ".//head/meta[@property='al:android:url'][contains(@content,'live?room_id=')]/@content",
                        ),
                        str,
                        re.compile(r"room_id=(\d+)"),
                        validate.get(1),
                    ),
                    validate.all(
                        validate.xml_xpath_string(
                            ".//script[@type='application/json'][@id='SIGI_STATE'][1]/text()",
                        ),
                        str,
                        validate.parse_json(),
                        {
                            "LiveRoom": {
                                "liveRoomUserInfo": {
                                    "user": {
                                        "roomId": str,
                                    },
                                },
                            },
                        },
                        validate.get(("LiveRoom", "liveRoomUserInfo", "user", "roomId")),
                    ),
                    validate.transform(lambda *_: None),
                ),
            ),
        )
        if not self.id:
            log.error("Could not find room ID")
            return

        log.debug(f"room_id={self.id}")

        live_detail = self.session.http.get(
            self._URL_API_LIVE_DETAIL.format(room_id=self.id),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status_code": 0,
                    "LiveRoomInfo": {
                        "status": int,
                        "title": str,
                        "ownerInfo": {"nickname": str},
                    },
                },
                validate.get("LiveRoomInfo"),
                validate.union_get(
                    "status",
                    ("ownerInfo", "nickname"),
                    "title",
                ),
            ),
        )
        status, self.author, self.title = live_detail
        if status == self._STATUS_OFFLINE:
            log.info("The channel is currently offline")
            return

        streams = self.session.http.get(
            self._URL_WEBCAST_ROOM_INFO.format(room_id=self.id),
            schema=validate.Schema(
                validate.parse_json(),
                {"data": {validate.optional("stream_url"): {"live_core_sdk_data": {"pull_data": {"stream_data": str}}}}},
                validate.get(("data", "stream_url")),
                validate.none_or_all(
                    validate.get(("live_core_sdk_data", "pull_data", "stream_data")),
                    validate.parse_json(),
                    {
                        "data": {
                            str: validate.all(
                                {
                                    "main": {
                                        "flv": validate.url(),
                                        "sdk_params": validate.all(
                                            validate.parse_json(),
                                            {
                                                "vbitrate": int,
                                            },
                                        ),
                                    },
                                },
                                validate.union_get(
                                    ("main", "flv"),
                                    ("main", "sdk_params", "vbitrate"),
                                ),
                            ),
                        },
                    },
                    validate.get("data"),
                ),
            ),
        )
        if not streams:
            log.error("The stream is inaccessible")
            return

        for name, (url, vbitrate) in streams.items():
            self.QUALITY_WEIGHTS[name] = vbitrate
            yield name, HTTPStream(self.session, url)


__plugin__ = TikTok
