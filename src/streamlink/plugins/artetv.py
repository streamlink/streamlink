"""Plugin for Arte.tv, bi-lingual art and culture channel."""

import logging
import re
from operator import itemgetter

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)
JSON_VOD_URL = "https://api.arte.tv/api/player/v1/config/{0}/{1}?platform=ARTE_NEXT"
JSON_LIVE_URL = "https://api.arte.tv/api/player/v1/livestream/{0}"

_url_re = re.compile(r"""
    https?://(?:\w+\.)?arte\.tv/(?:guide/)?
    (?P<language>[a-z]{2})/
    (?:
        (?:videos/)?(?P<video_id>(?!RC\-|videos)[^/]+?)/.+ | # VOD
        (?:direct|live)        # Live TV
    )
""", re.VERBOSE)

_video_schema = validate.Schema({
    "videoJsonPlayer": {
        "VSR": validate.any(
            [],
            {
                validate.text: {
                    "height": int,
                    "mediaType": validate.text,
                    "url": validate.text,
                    "versionProg": int,
                    "versionLibelle": validate.text
                },
            },
        )
    }
})


class ArteTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _create_stream(self, streams):
        variant, variantname = min([(stream["versionProg"], stream["versionLibelle"]) for stream in streams.values()],
                                   key=itemgetter(0))
        log.debug(f"Using the '{variantname}' stream variant")
        for sname, stream in streams.items():
            if stream["versionProg"] == variant:
                if stream["mediaType"] == "hls":
                    try:
                        streams = HLSStream.parse_variant_playlist(self.session, stream["url"])
                        yield from streams.items()
                    except OSError as err:
                        log.warning(f"Failed to extract HLS streams for {sname}/{stream['versionLibelle']}: {err}")

    def _get_streams(self):
        match = _url_re.match(self.url)
        language = match.group('language')
        video_id = match.group('video_id')
        if video_id is None:
            json_url = JSON_LIVE_URL.format(language)
        else:
            json_url = JSON_VOD_URL.format(language, video_id)
        res = self.session.http.get(json_url)
        video = self.session.http.json(res, schema=_video_schema)

        if not video["videoJsonPlayer"]["VSR"]:
            return

        vsr = video["videoJsonPlayer"]["VSR"]
        return self._create_stream(vsr)


__plugin__ = ArteTV
