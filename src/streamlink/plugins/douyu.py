"""
$description 斗鱼直播 - 以游戏直播为主的弹幕式互动直播平台
$url www.douyu.com
$type live
"""

import hashlib
import logging
import re
import time

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(
        r"https?://(?:www\.)?douyu\.com/(?:topic/)?(?P<rid>\d+)(?:\?.*dyshid=(?P<dyshid>[^&]+))?",
    ),
)
@pluginargument(
    "rate",
    metavar="RATE",
    default="0",
    help="Stream quality rate: 0=best (default), 1=smooth, 2=HD, 3=super HD, 4=4Mbps",
)
class Douyu(Plugin):
    _URL_ENCRYPTION = "https://www.douyu.com/wgapi/livenc/liveweb/websec/getEncryption"
    _URL_PLAY = "https://www.douyu.com/lapi/live/getH5PlayV1/{rid}"

    DID = "10000000000000000000000000001501"

    def _get_real_rid(self, rid: str) -> str:
        """Get real room ID (URL room ID may differ from actual rid)"""
        res = self.session.http.get(f"https://www.douyu.com/{rid}")

        # Method 1: Extract from $ROOM.room_id
        match = re.search(r"\$ROOM\.room_id\s*=\s*(\d+)", res.text)
        if match:
            return match.group(1)

        # Method 2: Extract from roomID
        match = re.search(r"roomID[\":\s]+(\d+)", res.text)
        if match:
            return match.group(1)

        # Method 3: Extract from canonical link
        match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'][^"\']*/(\d+)', res.text)
        if match:
            return match.group(1)

        # Method 4: Return input if it's already a number
        if rid.isdigit():
            return rid

        raise PluginError(f"Cannot get real room ID: {rid}")

    def _get_room_metadata(self, rid: str):
        """Get room metadata (streamer name, title, category, etc.)"""
        try:
            data = self.session.http.get(
                f"https://www.douyu.com/betard/{rid}",
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "room": {
                            "room_id": int,
                            "room_name": str,
                            "nickname": str,
                            "cate_name": str,
                            "show_status": int,  # 1=live, 2=offline
                        },
                    },
                    validate.get("room"),
                ),
            )
            self.id = str(data["room_id"])
            self.title = data["room_name"]
            self.author = data["nickname"]
            self.category = data["cate_name"]
            return data["show_status"] == 1
        except Exception:
            log.debug("Failed to get room metadata, continuing with stream extraction")
            return True  # Assume live, let subsequent steps determine

    @staticmethod
    def _compute_auth(rid: str, did: str, ts: int, key: str, rand_str: str, enc_time: int, is_special: int) -> str:
        """
        Compute auth signature parameter.

        Algorithm from douyuEx userscript:
        1. If is_special != 1, append rid + ts as suffix
        2. Start from rand_str, iterate enc_time times: md5(f + key)
        3. Final: md5(f + key + suffix) is the auth
        """
        suffix = "" if is_special == 1 else f"{rid}{ts}"
        f = rand_str
        for _ in range(enc_time):
            f = hashlib.md5((f + key).encode("utf-8")).hexdigest()
        return hashlib.md5((f + key + suffix).encode("utf-8")).hexdigest()

    def _get_stream_url(self, rid: str, rate: str, did: str | None = None) -> str | None:
        """
        Get actual live stream URL.

        Process:
        1. GET getEncryption to get encryption parameters
        2. Compute auth signature
        3. POST getH5PlayV1 to get stream URL
        """
        did = did or self.DID

        # Step 1: Get encryption parameters
        enc_data = self.session.http.get(
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

        if enc_data["error"] != 0 or not enc_data["data"]:
            log.error("Failed to get encryption parameters")
            return None

        d = enc_data["data"]
        ts = int(time.time())

        # Step 2: Compute auth
        auth = self._compute_auth(
            rid=rid,
            did=did,
            ts=ts,
            key=d["key"],
            rand_str=d["rand_str"],
            enc_time=d["enc_time"],
            is_special=d["is_special"],
        )

        # Step 3: Request stream URL
        play_data = self.session.http.post(
            self._URL_PLAY.format(rid=rid),
            data={
                "enc_data": d["enc_data"],
                "tt": str(ts),
                "did": did,
                "auth": auth,
                "cdn": "",
                "rate": rate,
                "hevc": "0",
                "fa": "0",
                "ive": "0",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "error": int,
                    "data": validate.any(
                        None,
                        {
                            "rtmp_url": str,
                            "rtmp_live": str,
                        },
                    ),
                },
            ),
        )

        if play_data["error"] != 0 or not play_data["data"]:
            error_code = play_data["error"]
            if error_code == 102:
                log.error("Room does not exist")
            elif error_code == 104:
                log.info("Room is offline")
            else:
                log.error(f"Failed to get stream URL (error={error_code})")
            return None

        url = f"{play_data['data']['rtmp_url']}/{play_data['data']['rtmp_live']}"
        return url

    def _get_streams(self):
        rid_input = self.match.group("rid")
        # Extract user DID from URL if available
        user_did = self.match.groupdict().get("dyshid")

        # Get real room ID
        real_rid = self._get_real_rid(rid_input)
        log.debug(f"Real room ID: {real_rid}")

        # Get room metadata
        is_live = self._get_room_metadata(real_rid)
        if not is_live:
            log.info("Streamer is offline")
            raise NoStreamsError

        # Get stream quality parameter
        rate = self.get_option("rate")

        # Get stream URL (prefer user DID if available)
        stream_url = self._get_stream_url(real_rid, rate, did=user_did)
        if not stream_url:
            raise NoStreamsError

        log.debug(f"Stream URL: {stream_url}")

        # Douyu CDN requires Referer header
        yield (
            "live",
            HTTPStream(
                self.session,
                stream_url,
                headers={"Referer": "https://www.douyu.com/"},
            ),
        )


__plugin__ = Douyu
