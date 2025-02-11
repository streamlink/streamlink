"""
$description South Korean live-streaming platform for individual live streams.
$url pandalive.co.kr
$type live
$metadata author
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:\w+\.)?pandalive\.co\.kr/(?:\w+/)?play/(?P<channel>[^/#?]+)"),
)
class Pandalive(Plugin):
    _URL_API_MEMBER = "https://api.pandalive.co.kr/v1/member/bj"

    def _get_streams(self):
        result, user_id = self.session.http.post(
            self._URL_API_MEMBER,
            data={"userId": self.match["channel"]},
            raise_for_status=False,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "result": False,
                            "message": str,
                        },
                        validate.union_get("result", "message"),
                    ),
                    validate.all(
                        {
                            "bjInfo": {
                                "idx": int,
                            },
                        },
                        validate.get(("bjInfo", "idx")),
                        validate.transform(lambda data: (True, data)),
                    ),
                ),
            ),
        )
        if not result:
            log.error(user_id or "Failed to get user ID")
            return
        if not user_id:
            return

        log.debug(f"{user_id=}")

        json = self.session.http.post(
            "https://api.pandalive.co.kr/v1/live/play",
            headers={
                "Referer": self.url,
            },
            data={
                "action": "watch",
                "userId": user_id,
            },
            acceptable_status=(200, 400),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "media": {
                            "title": str,
                            "userId": str,
                            "userNick": str,
                            "isPw": bool,
                            "isLive": bool,
                            "liveType": str,
                        },
                        "PlayList": {
                            validate.optional("hls"): [
                                {
                                    "url": validate.url(),
                                },
                            ],
                            validate.optional("hls2"): [
                                {
                                    "url": validate.url(),
                                },
                            ],
                            validate.optional("hls3"): [
                                {
                                    "url": validate.url(),
                                },
                            ],
                        },
                        "result": bool,
                        "message": str,
                    },
                    {
                        "result": bool,
                        "message": str,
                    },
                ),
            ),
        )

        if not json["result"]:
            log.error(json["message"])
            return

        if not json["media"]["isLive"]:
            log.error("The broadcast has ended")
            return

        if json["media"]["isPw"]:
            log.error("The broadcast is password protected")
            return

        log.info(f"Broadcast type: {json['media']['liveType']}")

        self.author = f"{json['media']['userNick']} ({json['media']['userId']})"
        self.title = f"{json['media']['title']}"

        playlist = json["PlayList"]
        for key in ("hls", "hls2", "hls3"):
            # use the first available HLS stream
            if not playlist.get(key):
                continue
            # all stream qualities share the same URL, so just use the first one
            return HLSStream.parse_variant_playlist(
                self.session,
                playlist[key][0]["url"],
                headers={
                    "Origin": "https://www.pandalive.co.kr",
                    "Referer": self.url,
                },
            )


__plugin__ = Pandalive
