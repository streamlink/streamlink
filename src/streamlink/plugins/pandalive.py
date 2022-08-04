"""
$description South Korean live-streaming platform for individual live streams.
$url pandalive.co.kr
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?pandalive\.co\.kr/"
))
class Pandalive(Plugin):
    def _get_streams(self):
        media_code = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""routePath:\s*(?P<q>["'])(\\u002F|/)live(\\u002F|/)play(\\u002F|/)(?P<id>.+?)(?P=q)"""),
            validate.any(None, validate.get("id")),
        ))

        if not media_code:
            return

        log.debug(f"Media code: {media_code}")

        json = self.session.http.post(
            "https://api.pandalive.co.kr/v1/live/play",
            data={
                "action": "watch",
                "userId": media_code,
            },
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
                            validate.optional("hls"): [{
                                "url": validate.url(),
                            }],
                            validate.optional("hls2"): [{
                                "url": validate.url(),
                            }],
                            validate.optional("hls3"): [{
                                "url": validate.url(),
                            }],
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
            if key in playlist and playlist[key]:
                # all stream qualities share the same URL, so just use the first one
                return HLSStream.parse_variant_playlist(self.session, playlist[key][0]["url"])


__plugin__ = Pandalive
