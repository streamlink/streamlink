"""
$description British music live-streaming platform for radio shows and DJ mixes.
$url mixcloud.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:www\.)?mixcloud\.com/live/(?P<user>[^/]+)"))
class Mixcloud(Plugin):
    def _get_streams(self):
        data = self.session.http.post(
            "https://www.mixcloud.com/graphql",
            json={
                "query": """
                    query streamData($user: UserLookup!) {
                        userLookup(lookup: $user) {
                            id
                            displayName
                            liveStream(isPublic: false) {
                                name
                                streamStatus
                                hlsUrl
                            }
                        }
                    }
                """,
                "variables": {"user": {"username": self.match.group("user")}},
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "userLookup": validate.none_or_all(
                            {
                                "id": str,
                                "displayName": str,
                                "liveStream": {
                                    "name": str,
                                    "streamStatus": validate.any("ENDED", "LIVE"),
                                    "hlsUrl": validate.none_or_all(validate.url()),
                                },
                            },
                        ),
                    },
                },
                validate.get(("data", "userLookup")),
            ),
        )
        if not data:
            log.error("User not found")
            return

        self.id = data.get("id")
        self.author = data.get("displayName")
        data = data.get("liveStream")

        if data.get("streamStatus") == "ENDED":
            log.info("This stream has ended")
            return

        self.title = data.get("name")

        if data.get("hlsUrl"):
            return HLSStream.parse_variant_playlist(self.session, data.get("hlsUrl"))


__plugin__ = Mixcloud
