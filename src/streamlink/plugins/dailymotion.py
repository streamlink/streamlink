"""
$description Global live-streaming and video on-demand hosting platform.
$url dailymotion.com
$url lequipe.fr
$type live, vod
$metadata id
$metadata author
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="user",
    pattern=re.compile(r"https?://(?:\w+\.)?dailymotion\.com/(?P<user>(?!embed|video|live)[\w-]+)"),
)
@pluginmatcher(
    name="media",
    pattern=re.compile(r"https?://(?:\w+\.)?dailymotion\.com/(?:embed/)?(?:video|live)/(?P<media_id>[^_?/]+)"),
)
@pluginmatcher(
    name="lequipe",
    pattern=re.compile(r"https?://(?:\w+\.)?lequipe\.fr/tv/"),
)
class DailyMotion(Plugin):
    _URL_API_USER_VIDEO = "https://api.dailymotion.com/user/{user}/videos"
    _URL_STREAM_INFO = "https://www.dailymotion.com/player/metadata/video/{media_id}"

    def _get_streams_from_media(self, media_id, params=None):
        media = self.session.http.get(
            self._URL_STREAM_INFO.format(media_id=media_id),
            params=params,
            cookies={
                "family_filter": "off",
                "ff": "off",
            },
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "error": {"type": "not_found"},
                    },
                    {
                        "error": {"title": str},
                    },
                    {
                        "owner": {
                            "username": str,
                        },
                        "title": str,
                        "qualities": {
                            str: [
                                {
                                    "type": str,
                                    "url": validate.url(),
                                },
                            ],
                        },
                    },
                ),
            ),
        )

        error = media.get("error")
        if error:
            if error.get("type") == "not_found":
                log.error(f"Unknown media ID: {media_id}")
            else:
                log.error(f"Failed to get stream: {error['title']}")
            return

        self.id = media_id
        self.author = media["owner"]["username"]
        self.title = media["title"]

        for quality, streams in media["qualities"].items():
            for stream in streams:
                if stream["type"] == "application/x-mpegURL":
                    if quality != "auto":
                        # Avoid duplicate HLS streams with bitrate selector in the URL query
                        continue
                    yield from HLSStream.parse_variant_playlist(self.session, stream["url"]).items()
                elif stream["type"] == "video/mp4":
                    # Drop FPS in quality
                    quality = re.sub(r"@\d+", "", quality)
                    resolution = f"{quality}p"
                    yield resolution, HTTPStream(self.session, stream["url"])

    def _get_media_id(self, user):
        # https://developers.dailymotion.com/tools/
        data = self.session.http.get(
            self._URL_API_USER_VIDEO.format(user=user),
            params={
                "fields": "id",
                "flags": "live_onair",
                "family_filter": "false",
            },
            acceptable_status=(200, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {
                        "error": {"message": str},
                    },
                    {
                        "list": [{"id": str}],
                    },
                ),
            ),
        )

        if data.get("error"):
            log.error(f"Error while retrieving media ID: {data['error']['message']}")
            return

        if not data["list"]:
            log.error(f"No live streams found for channel {user}")
            return

        return data["list"][0]["id"]

    def _get_embedder_media_id(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string("""
                    .//script
                    [@type='application/ld+json']
                    [contains(text(),'https://www.dailymotion.com/embed/video/')]
                    [1]
                    /text()
                """),
                validate.none_or_all(
                    validate.parse_json(),
                    {
                        "@type": "VideoObject",
                        "embedUrl": validate.url(
                            netloc=validate.endswith("dailymotion.com"),
                            path=validate.startswith("/embed/video/"),
                        ),
                    },
                    validate.get("embedUrl"),
                    validate.transform(lambda url: url.rsplit("/", 1)[-1]),
                ),
            ),
        )

    def _get_streams(self):
        params = {}
        if self.matches["media"]:
            media_id = self.match["media_id"]
        elif self.matches["user"]:
            media_id = self._get_media_id(self.match["user"])
        else:
            media_id = self._get_embedder_media_id()
            params["embedder"] = self.url

        if media_id:
            log.debug(f"Found media ID: {media_id}")
            return self._get_streams_from_media(media_id, params=params)


__plugin__ = DailyMotion
