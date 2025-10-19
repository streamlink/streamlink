"""
$description South Korean live-streaming platform for gaming, entertainment, and other creative content. Owned by Naver.
$url chzzk.naver.com
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


class ChzzkHLSStreamWorker(HLSStreamWorker):
    """Custom HLS stream worker that adds __bgda__ query parameter to segment URLs"""

    reader: "ChzzkHLSStreamReader"
    stream: "ChzzkHLSStream"

    def process_segments(self, playlist):
        """Override process_segments to add __bgda__ parameter to segment URIs"""

        # Only modify segments if we have bgda_param
        if hasattr(self.stream, "bgda_param") and self.stream.bgda_param:
            for segment in playlist.segments:
                # Only modify .m4v segments and if __bgda__ parameter doesn't already exist
                if ".m4v" in segment.uri and "__bgda__" not in segment.uri:
                    segment.uri = update_qsd(segment.uri, {"__bgda__": self.stream.bgda_param}, safe="=")

        return super().process_segments(playlist)


class ChzzkHLSStreamReader(HLSStreamReader):
    __worker__ = ChzzkHLSStreamWorker

    worker: "ChzzkHLSStreamWorker"
    stream: "ChzzkHLSStream"


class ChzzkHLSStream(HLSStream):
    """Custom HLS stream that adds __bgda__ query parameter to segment URLs"""

    __reader__ = ChzzkHLSStreamReader

    def __init__(self, session, url, bgda_param=None, **kwargs):
        self.bgda_param = bgda_param
        super().__init__(session, url, **kwargs)


class ChzzkAPI:
    _CHANNELS_LIVE_DETAIL_URL = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
    _CHANNELS_LIVE_PLAYBACK_URL = "https://api.chzzk.naver.com/service/v1/channels/{channel_id}/live-playback-json"
    _VIDEOS_URL = "https://api.chzzk.naver.com/service/v2/videos/{video_id}"
    _CLIP_URL = "https://api.chzzk.naver.com/service/v1/play-info/clip/{clip_id}"

    _LIVE_PLAYBACK_JSON_SCHEMA = validate.none_or_all(
        str,
        validate.parse_json(),
        {
            "media": [
                validate.all(
                    {
                        "mediaId": str,
                        "protocol": str,
                        "path": validate.url(),
                    },
                    validate.union_get(
                        "mediaId",
                        "protocol",
                        "path",
                    ),
                ),
            ],
        },
        validate.get("media"),
    )

    def __init__(self, session):
        self._session = session

    def _query_api(self, url, *schemas):
        return self._session.http.get(
            url,
            acceptable_status=(200, 400, 404),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "code": int,
                            "message": str,
                        },
                        validate.transform(lambda data: ("error", data["message"])),
                    ),
                    validate.all(
                        {
                            "code": 200,
                            "content": None,
                        },
                        validate.transform(lambda _: ("success", None)),
                    ),
                    validate.all(
                        {
                            "code": 200,
                            "content": dict,
                        },
                        validate.get("content"),
                        *schemas,
                        validate.transform(lambda data: ("success", data)),
                    ),
                ),
            ),
        )

    def get_live_detail(self, channel_id):
        return self._query_api(
            self._CHANNELS_LIVE_DETAIL_URL.format(channel_id=channel_id),
            {
                "status": str,
                "liveId": int,
                "liveTitle": validate.any(str, None),
                "liveCategory": validate.any(str, None),
                "adult": bool,
                "channel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
                "livePlaybackJson": self._LIVE_PLAYBACK_JSON_SCHEMA,
                "timeMachineActive": bool,
            },
            validate.union_get(
                "livePlaybackJson",
                "status",
                "liveId",
                "channel",
                "liveCategory",
                "liveTitle",
                "adult",
                "timeMachineActive",
            ),
        )

    def get_live_playback(self, channel_id):
        return self._query_api(
            self._CHANNELS_LIVE_PLAYBACK_URL.format(channel_id=channel_id),
            {
                "playbackJson": self._LIVE_PLAYBACK_JSON_SCHEMA,
            },
            validate.get(
                "playbackJson",
            ),
        )

    def get_videos(self, video_id):
        return self._query_api(
            self._VIDEOS_URL.format(video_id=video_id),
            {
                "inKey": validate.any(str, None),
                "videoNo": validate.any(int, None),
                "videoId": validate.any(str, None),
                "videoTitle": validate.any(str, None),
                "videoCategory": validate.any(str, None),
                "adult": bool,
                "channel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
                "liveRewindPlaybackJson": self._LIVE_PLAYBACK_JSON_SCHEMA,
            },
            validate.union_get(
                "adult",
                "inKey",
                "videoId",
                "liveRewindPlaybackJson",
                "videoNo",
                "channel",
                "videoTitle",
                "videoCategory",
            ),
        )

    def get_clips(self, clip_id):
        return self._query_api(
            self._CLIP_URL.format(clip_id=clip_id),
            {
                validate.optional("inKey"): validate.any(str, None),
                validate.optional("videoId"): validate.any(str, None),
                "contentId": str,
                "contentTitle": str,
                "adult": bool,
                "ownerChannel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
            },
            validate.union((
                validate.get("adult"),
                validate.get("inKey"),
                validate.get("videoId"),
                validate.get("contentId"),
                validate.get("ownerChannel"),
                validate.get("contentTitle"),
                validate.transform(lambda _: None),
            )),
        )


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://chzzk\.naver\.com/live/(?P<channel_id>[^/?]+)",
    ),
)
@pluginmatcher(
    name="video",
    pattern=re.compile(
        r"https?://chzzk\.naver\.com/video/(?P<video_id>[^/?]+)",
    ),
)
@pluginmatcher(
    name="clip",
    pattern=re.compile(
        r"https?://chzzk\.naver\.com/clips/(?P<clip_id>[^/?]+)",
    ),
)
class Chzzk(Plugin):
    _API_VOD_PLAYBACK_URL = "https://apis.naver.com/neonplayer/vodplay/v2/playback/{video_id}?key={in_key}"

    _STATUS_OPEN = "OPEN"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api = ChzzkAPI(self.session)

    def _get_live_playback(self, playback):
        for media_id, media_protocol, media_path in playback:
            if media_protocol == "HLS" and media_id == "HLS":
                # Extract __bgda__ parameter from the media path URL
                parsed_url = urlparse(media_path)
                bgda_param = dict(parse_qsl(parsed_url.query)).get("hdnts")
                yield from ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    bgda_param=bgda_param,
                    ffmpeg_options={"copyts": True},
                ).items()
                return

    def _get_live(self, channel_id):
        datatype, data = self._api.get_live_detail(channel_id)
        if datatype == "error":
            log.error(data)
            return
        if data is None:
            return

        media, status, self.id, self.author, self.category, self.title, adult, timeMachineActive = data
        if status != self._STATUS_OPEN:
            log.error("The stream is unavailable")
            return
        if media is None:
            log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
            return

        if timeMachineActive:
            log.info("Time machine is active, attempting to get playback streams")
            datatype_playback, data_playback = self._api.get_live_playback(channel_id)
            if datatype_playback != "error" and data_playback is not None:
                yield from self._get_live_playback(data_playback)
                return

        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                yield from HLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    ffmpeg_options={"copyts": True},
                ).items()
                return

    def _get_vod_playback(self, datatype, data):
        if datatype == "error":
            log.error(data)
            return

        adult, in_key, vod_id, live_rewind_playback_json, *metadata = data

        if in_key is not None and vod_id is not None:
            self.id, self.author, self.title, self.category = metadata

            for name, stream in DASHStream.parse_manifest(
                self.session,
                self._API_VOD_PLAYBACK_URL.format(video_id=vod_id, in_key=in_key),
                headers={"Accept": "application/dash+xml"},
            ).items():
                if stream.video_representation and stream.video_representation.mimeType == "video/mp2t":
                    yield name, stream
            return

        if live_rewind_playback_json is not None:
            log.info("The video might not be fully encoded, attempting to get playback streams")
            self.id, self.author, self.title, self.category = metadata
            yield from self._get_live_playback(live_rewind_playback_json)
            return

        log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
        return

    def _get_video(self, video_id):
        return self._get_vod_playback(
            *self._api.get_videos(video_id),
        )

    def _get_clip(self, clip_id):
        return self._get_vod_playback(
            *self._api.get_clips(clip_id),
        )

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])
        elif self.matches["video"]:
            return self._get_video(self.match["video_id"])
        elif self.matches["clip"]:
            return self._get_clip(self.match["clip_id"])


__plugin__ = Chzzk
