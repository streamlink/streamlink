"""
$description South Korean live-streaming platform for gaming, entertainment, and other creative content. Owned by Naver.
$url chzzk.naver.com
$type live, vod
"""

import logging
import re
import time

from streamlink.exceptions import StreamError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker, parse_m3u8


log = logging.getLogger(__name__)


class ChzzkHLSStreamWorker(HLSStreamWorker):
    stream: "ChzzkHLSStream"

    def _fetch_playlist(self):
        try:
            return super()._fetch_playlist()
        except StreamError as err:
            if err.err.response.status_code >= 400:
                self.stream.refresh_playlist()
                log.warning(f"Force-reloading the channel playlist on error: {err}")
            raise err


class ChzzkHLSStreamReader(HLSStreamReader):
    __worker__ = ChzzkHLSStreamWorker


class ChzzkHLSStream(HLSStream):
    __shortname__ = "hls-chzzk"
    __reader__ = ChzzkHLSStreamReader

    _EXPIRE = re.compile(r"exp=(\d+)")
    _REFRESH_BEFORE = 3 * 60 * 60  # 3 hours

    def __init__(self, session, url, channel_id, *args, **kwargs):
        super().__init__(session, url, *args, **kwargs)
        self._url = url
        self._channel_id = channel_id
        self._api = ChzzkAPI(session)

    def refresh_playlist(self):
        log.debug("Refreshing the stream URL to get a new token.")
        datatype, data = self._api.get_live_detail(self._channel_id)
        if datatype == "error":
            raise StreamError(data)
        media, status, *_ = data
        if status != "OPEN" or media is None:
            raise StreamError("Error occurred while refreshing the stream URL.")
        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                media_uri = self._get_media_uri(media_path)
                self._replace_token_from(media_uri)
                log.debug(f"Refreshed the stream URL to {self._url}")
                break

    def _get_media_uri(self, media_path):
        res = self._fetch_variant_playlist(self.session, media_path)
        m3u8 = parse_m3u8(res)
        return m3u8.playlists[0].uri

    def _get_token_from(self, path):
        return path.split("/")[-2]

    def _replace_token_from(self, media_uri):
        prev_token = self._get_token_from(self._url)
        current_token = self._get_token_from(media_uri)
        self._url = self._url.replace(prev_token, current_token)

    def _should_refresh(self):
        return self._expire is not None and time.time() >= self._expire - self._REFRESH_BEFORE

    @property
    def _expire(self):
        match = self._EXPIRE.search(self._url)
        if match:
            return int(match.group(1))
        return None

    @property
    def url(self):
        if self._should_refresh():
            self.refresh_playlist()
        return self._url


class ChzzkAPI:
    _CHANNELS_LIVE_DETAIL_URL = "https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
    _VIDEOS_URL = "https://api.chzzk.naver.com/service/v2/videos/{video_id}"

    def __init__(self, session):
        self._session = session

    def _query_api(self, url, *schemas):
        return self._session.http.get(
            url,
            acceptable_status=(200, 404),
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
                        validate.transform(lambda data: ("success", None)),
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
                "livePlaybackJson": validate.none_or_all(
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
                ),
            },
            validate.union_get(
                "livePlaybackJson",
                "status",
                "liveId",
                "channel",
                "liveCategory",
                "liveTitle",
                "adult",
            ),
        )

    def get_videos(self, video_id):
        return self._query_api(
            self._VIDEOS_URL.format(video_id=video_id),
            {
                "inKey": validate.any(str, None),
                "videoId": validate.any(str, None),
                "videoTitle": validate.any(str, None),
                "videoCategory": validate.any(str, None),
                "adult": bool,
                "channel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
            },
            validate.union_get(
                "inKey",
                "videoId",
                "channel",
                "videoCategory",
                "videoTitle",
                "adult",
            ),
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
class Chzzk(Plugin):
    _API_VOD_PLAYBACK_URL = "https://apis.naver.com/neonplayer/vodplay/v2/playback/{video_id}?key={in_key}"

    _STATUS_OPEN = "OPEN"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api = ChzzkAPI(self.session)

    def _get_live(self, channel_id, live_check_only=False):
        datatype, data = self._api.get_live_detail(channel_id)
        if datatype == "error":
            log.error(data)
            return
        if data is None:
            return

        media, status, self.id, self.author, self.category, self.title, adult = data
        if status != self._STATUS_OPEN:
            log.debug("The stream is not live.")
            return

        if media is None:
            log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
            return

        self.is_live = True

        if live_check_only:
            return

        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                return ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    channel_id=channel_id,
                    ffmpeg_options={"copyts": True},
                )

    def _get_video(self, video_id):
        datatype, data = self._api.get_videos(video_id)
        if datatype == "error":
            log.error(data)
            return

        self.id = video_id
        in_key, vod_id, self.author, self.category, self.title, adult = data

        if in_key is None or vod_id is None:
            log.error(f"This stream is {'for adults only' if adult else 'unavailable'}")
            return

        for name, stream in DASHStream.parse_manifest(
            self.session,
            self._API_VOD_PLAYBACK_URL.format(video_id=vod_id, in_key=in_key),
            headers={"Accept": "application/dash+xml"},
        ).items():
            if stream.video_representation.mimeType == "video/mp2t":
                yield name, stream

    def _get_streams(self, live_check_only=False):
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"], live_check_only)
        elif self.matches["video"]:
            return self._get_video(self.match["video_id"])


__plugin__ = Chzzk
