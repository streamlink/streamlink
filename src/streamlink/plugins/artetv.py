"""Plugin for Arte.tv, bi-lingual art and culture channel."""

import logging
import re
from operator import itemgetter

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)
JSON_VOD_URL = "https://api.arte.tv/api/player/v2/config/{0}/{1}"
JSON_LIVE_URL = "https://api.arte.tv/api/player/v2/config/{0}/LIVE"
V2_API_BEARER = "MzYyZDYyYmM1Y2Q3ZWRlZWFjMmIyZjZjNTRiMGY4MzY4NzBhOWQ5YjE4MGQ1NGFiODJmOTFlZDQwN2FkOTZjMQ"

_video_schema = validate.Schema({
    "data": {
        "attributes": {
            "streams": validate.any(
                [],
                [{
                    "url": validate.url(),
                    "slot": int,
                    "protocol": validate.text,
                    "versions": validate.all(
                        [{
                            "label": validate.text
                        }],
                        validate.transform(lambda x: x[0])
                    )
                }]
            )
        }
    },
})


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
    def _create_stream(self, streams):
        variant, variantname = min([(stream["slot"], stream["versions"]["label"]) for stream in streams],
                                   key=itemgetter(0))
        log.debug(f"Using the '{variantname}' stream variant")
        for stream in streams:
            if stream["slot"] == variant:
                if "hls" in stream["protocol"].lower():
                    try:
                        streams = HLSStream.parse_variant_playlist(self.session, stream["url"])
                        yield from streams.items()
                    except OSError as err:
                        log.warning(f"Failed to extract HLS streams for {stream['versions']['label']}: {err}")

    def _get_streams(self):
        language = self.match.group('language')
        video_id = self.match.group('video_id')
        if video_id is None:
            json_url = JSON_LIVE_URL.format(language)
        else:
            json_url = JSON_VOD_URL.format(language, video_id)
        res = self.session.http.get(json_url, headers={"Authorization": "Bearer {}".format(V2_API_BEARER)})
        video = self.session.http.json(res, schema=_video_schema)

        if not (vsr := video["data"]["attributes"]["streams"]):
            return

        return self._create_stream(vsr)


__plugin__ = ArteTV

