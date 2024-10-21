"""
$description European public service channel promoting culture, including magazine shows, concerts and documentaries.
$url arte.tv
$type live, vod
$metadata id
$metadata title
"""

import logging
import re
from operator import itemgetter

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:\w+\.)?arte\.tv/(?P<language>[a-z]{2})/(?:direct|live)/?",
    ),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(
        r"https?://(?:\w+\.)?arte\.tv/(?:guide/)?(?P<language>[a-z]{2})/(?:videos/)?(?P<video_id>(?!RC-|videos)[^/]+?)/.+",
    ),
)
class ArteTV(Plugin):
    API_URL = "https://api.arte.tv/api/player/v2/config/{language}/{id}"

    def _get_streams(self):
        self.id = self.match["video_id"] if self.matches["vod"] else "LIVE"

        json_url = self.API_URL.format(
            language=self.match["language"],
            id=self.id,
        )
        streams, metadata = self.session.http.get(
            json_url,
            schema=validate.Schema(
                validate.parse_json(),
                {"data": {"attributes": dict}},
                validate.get(("data", "attributes")),
                {
                    "streams": validate.any(
                        [],
                        [
                            validate.all(
                                {
                                    "slot": int,
                                    "protocol": str,
                                    "url": validate.url(),
                                },
                                validate.union_get("slot", "protocol", "url"),
                            ),
                        ],
                    ),
                    "metadata": {
                        "title": str,
                        "subtitle": validate.any(None, str),
                    },
                },
                validate.union_get("streams", "metadata"),
            ),
        )

        self.title = f"{metadata['title']} - {metadata['subtitle']}" if metadata["subtitle"] else metadata["title"]

        for _slot, protocol, url in sorted(streams, key=itemgetter(0)):
            if "HLS" not in protocol:
                continue
            return HLSStream.parse_variant_playlist(self.session, url)


__plugin__ = ArteTV
