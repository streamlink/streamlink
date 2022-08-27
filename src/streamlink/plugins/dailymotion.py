"""
$description Global live streaming and video on-demand hosting platform.
$url dailymotion.com
$type live, vod
"""

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)

COOKIES = {
    "family_filter": "off",
    "ff": "off"
}
STREAM_INFO_URL = "https://www.dailymotion.com/player/metadata/video/{0}"
USER_INFO_URL = "https://api.dailymotion.com/user/{0}"

_media_schema = validate.Schema(validate.any(
    {"error": {"title": validate.text}},
    # "stream_chromecast_url": validate.url(),
    # Chromecast URL is already available in qualities subdict
    {"qualities": validate.any({
        validate.text: validate.all([{
            "type": validate.text,
            "url": validate.url()
        }])
    })
    }))
_live_id_schema = validate.Schema(
    {
        "total": int,
        "list": validate.any(
            [],
            [{"id": validate.text}]
        )
    }
)


@pluginmatcher(re.compile(r"""
    https?://(?:\w+\.)?dailymotion\.com
    (?:
        (/embed)?/(video|live)/(?P<media_id>[^_?/]+)
        |
        /(?P<channel_name>[\w-]+)
    )
""", re.VERBOSE))
class DailyMotion(Plugin):
    def _get_streams_from_media(self, media_id):
        res = self.session.http.get(STREAM_INFO_URL.format(media_id), cookies=COOKIES)
        media = self.session.http.json(res, schema=_media_schema)

        if media.get("error"):
            log.error("Failed to get stream: {0}".format(media["error"]["title"]))
            return

        for quality, streams in media['qualities'].items():
            for stream in streams:
                if stream['type'] == 'application/x-mpegURL':
                    if quality != 'auto':
                        # Avoid duplicate HLS streams with bitrate selector in the URL query
                        continue
                    yield from HLSStream.parse_variant_playlist(self.session, stream['url']).items()
                elif stream['type'] == 'video/mp4':
                    # Drop FPS in quality
                    resolution = re.sub('@[0-9]+', '', quality) + 'p'
                    yield resolution, HTTPStream(self.session, stream['url'])

    def get_live_id(self, username):
        """Get the livestream videoid from a username.
           https://developer.dailymotion.com/tools/apiexplorer#/user/videos/list
        """
        params = {
            "flags": "live_onair"
        }
        api_user_videos = f"{USER_INFO_URL.format(username)}/videos"
        try:
            res = self.session.http.get(
                api_user_videos.format(username),
                params=params
            )
        except Exception:
            log.error("invalid username")
            raise NoStreamsError(self.url)

        data = self.session.http.json(res, schema=_live_id_schema)
        if data["total"] > 0:
            media_id = data["list"][0]["id"]
            return media_id
        return False

    def _get_streams(self):
        media_id = self.match.group("media_id")
        username = self.match.group("channel_name")

        if not media_id and username:
            media_id = self.get_live_id(username)

        if media_id:
            log.debug("Found media ID: {0}".format(media_id))
            return self._get_streams_from_media(media_id)


__plugin__ = DailyMotion
