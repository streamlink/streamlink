"""
$description European public service channel promoting culture, including magazine shows, concerts and documentaries.
$url arte.tv
$type live, vod
"""

import logging
import re
from operator import itemgetter

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:\w+\.)?arte\.tv/(?:guide/)?
    (?P<language>[a-z]{2})/
    (?:
        (?:videos/)?(?P<video_id>(?!RC-|videos)[^/]+?)/.+
        |
        (?:direct|live)
    )
""", re.VERBOSE))
class ArteTV(Plugin):
    API_URL = "https://api.arte.tv/api/player/v2/config/{0}/{1}"
    API_TOKEN = "MzYyZDYyYmM1Y2Q3ZWRlZWFjMmIyZjZjNTRiMGY4MzY4NzBhOWQ5YjE4MGQ1NGFiODJmOTFlZDQwN2FkOTZjMQ"

    def _get_streams(self):
        language = self.match.group("language")
        video_id = self.match.group("video_id")

        json_url = self.API_URL.format(language, video_id or "LIVE")
        headers = {
            "Authorization": f"Bearer {self.API_TOKEN}"
        }
        streams, metadata = self.session.http.get(json_url, headers=headers, schema=validate.Schema(
            validate.parse_json(),
            {"data": {"attributes": {
                "streams": validate.any(
                    [],
                    [
                        validate.all(
                            {
                                "url": validate.url(),
                                "slot": int,
                                "protocol": validate.any("HLS", "HLS_NG"),
                            },
                            validate.union_get("slot", "protocol", "url")
                        )
                    ]
                ),
                "metadata": {
                    "title": str,
                    "subtitle": validate.any(None, str)
                }
            }}},
            validate.get(("data", "attributes")),
            validate.union_get("streams", "metadata")
        ))

        if not streams:
            return

        self.title = f"{metadata['title']} - {metadata['subtitle']}" if metadata["subtitle"] else metadata["title"]

        for slot, protocol, url in sorted(streams, key=itemgetter(0)):
            return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = ArteTV
