"""
$description Chinese live-streaming platform for live video game broadcasts, operated by Douyu Technology.
$url www.douyu.com
$type live
$metadata id
$metadata author
$metadata category
$metadata title
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
import time
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.parse import parse_qsd


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:www\.)?douyu\.com/(?:topic/)?(?P<rid>\d+)",
    ),
)
class Douyu(Plugin):
    _URL_ENCRYPTION = "https://www.douyu.com/wgapi/livenc/liveweb/websec/getEncryption"
    _URL_PLAY = "https://www.douyu.com/lapi/live/getH5PlayV1/{rid}"
    _URL_BETARD = "https://www.douyu.com/betard/{rid}"

    DID = "10000000000000000000000000001501"
    HEVC = "0"
    FA = "0"
    IVE = "0"

    QUALITY_WEIGHTS: dict[str, int] = {}

    @classmethod
    def stream_weight(cls, stream: str) -> tuple[float, str]:
        weight = cls.QUALITY_WEIGHTS.get(stream)
        if weight:
            return weight, "douyu"
        return super().stream_weight(stream)

    def _get_room_metadata(self, rid: str) -> bool:
        try:
            data = self.session.http.get(
                self._URL_BETARD.format(rid=rid),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "room": {
                            "room_id": int,
                            "room_name": str,
                            "nickname": str,
                            validate.optional("cate_name"): validate.any(None, str),
                            "show_status": int,
                        },
                    },
                    validate.get("room"),
                ),
            )
            self.id = str(data["room_id"])
            self.title = data["room_name"]
            self.author = data["nickname"]
            self.category = data.get("cate_name")
            return data["show_status"] == 1
        except Exception:
            log.debug("Failed to get room metadata")
            return True

    @staticmethod
    def _compute_auth(rid: str, ts: int, key: str, rand_str: str, enc_time: int, is_special: int) -> str:
        suffix = "" if is_special == 1 else f"{rid}{ts}"
        f = rand_str
        for _ in range(enc_time):
            f = hashlib.md5((f + key).encode("utf-8")).hexdigest()
        return hashlib.md5((f + key + suffix).encode("utf-8")).hexdigest()

    def _request_stream(self, rid: str, rate: int, did: str, enc_data: dict, auth: str) -> dict | None:
        ts = int(time.time())
        play_data = self.session.http.post(
            self._URL_PLAY.format(rid=rid),
            data={
                "enc_data": enc_data["enc_data"],
                "tt": str(ts),
                "did": did,
                "auth": auth,
                "cdn": "",
                "rate": str(rate),
                "hevc": self.HEVC,
                "fa": self.FA,
                "ive": self.IVE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "error": int,
                    "data": validate.any(
                        None,
                        "",
                        {
                            "rtmp_url": validate.url(scheme="https"),
                            "rtmp_live": str,
                            validate.optional("multirates"): [{"name": str, "rate": int, "bit": int}],
                        },
                    ),
                },
            ),
        )

        if play_data["error"] != 0 or not play_data["data"]:
            return None

        return play_data["data"]

    def _get_streams(self):
        rid = self.match.group("rid")

        params = parse_qsd(urlparse(self.url).query)
        did = params.get("dyshid") or self.DID

        if not self._get_room_metadata(rid):
            log.info("Streamer is offline")
            return

        enc_response = self.session.http.get(
            self._URL_ENCRYPTION,
            params={"did": did},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "error": int,
                    "data": validate.any(
                        None,
                        {
                            "key": str,
                            "rand_str": str,
                            "enc_time": int,
                            "enc_data": str,
                            "is_special": int,
                        },
                    ),
                },
            ),
        )

        if enc_response["error"] != 0 or not enc_response["data"]:
            log.error("Failed to get encryption parameters")
            return

        enc_data = enc_response["data"]
        ts = int(time.time())
        auth = self._compute_auth(
            rid=rid,
            ts=ts,
            key=enc_data["key"],
            rand_str=enc_data["rand_str"],
            enc_time=enc_data["enc_time"],
            is_special=enc_data["is_special"],
        )

        first_data = self._request_stream(rid, 0, did, enc_data, auth)
        if not first_data:
            log.error("Failed to get stream URL")
            return

        multirates = first_data.get("multirates", [])

        if not multirates:
            url = f"{first_data['rtmp_url']}/{first_data['rtmp_live']}"
            self.QUALITY_WEIGHTS["source"] = sys.maxsize
            yield (
                "source",
                HTTPStream(
                    self.session,
                    url,
                    headers={"Referer": "https://www.douyu.com/"},
                ),
            )
            return

        for rate_info in multirates:
            rate = rate_info["rate"]
            bit = rate_info["bit"]
            name = f"{bit}k" if bit else "source"
            weight = bit or sys.maxsize
            self.QUALITY_WEIGHTS[name] = weight

            if rate == 0:
                data = first_data
            else:
                data = self._request_stream(rid, rate, did, enc_data, auth)

            if data:
                url = f"{data['rtmp_url']}/{data['rtmp_live']}"
                yield (
                    name,
                    HTTPStream(
                        self.session,
                        url,
                        headers={"Referer": "https://www.douyu.com/"},
                    ),
                )

        log.debug("QUALITY_WEIGHTS: %r", self.QUALITY_WEIGHTS)


__plugin__ = Douyu
