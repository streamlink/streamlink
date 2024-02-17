"""
$description South Korean live-streaming platform for gaming, entertainment, and other creative content. Owned by Naver.
$url chzzk.naver.com
$type live, vod
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Union
from streamlink.exceptions import StreamError

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.session import Streamlink
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.hls.hls import HLSStreamReader, HLSStreamWorker, MuxedHLSStream
from streamlink.stream.hls.m3u8 import M3U8, parse_m3u8

from streamlink.stream.hls.segment import Media


log = logging.getLogger(__name__)


class ChzzkHLSStreamWorker(HLSStreamWorker):
    stream: "ChzzkHLSStream"

    def _fetch_playlist(self):
        try:
            return super()._fetch_playlist()
        except StreamError as err:
            if err.err.response.status_code >= 400:
                self.stream.refresh_playlist()
                log.debug(
                    f"Force-reloading the channel playlist on error: {err}")
            raise err


class ChzzkHLSStreamReader(HLSStreamReader):
    __worker__ = ChzzkHLSStreamWorker


class ChzzkHLSStream(HLSStream):
    __shortname__ = "hls-chzzk"
    __reader__ = ChzzkHLSStreamReader

    _EXPIRE = re.compile(r"exp=(\d+)")
    _REFRESH_BEFORE = 3 * 60 * 60  # 3 hours

    def __init__(self, session, url, channel, *args, **kwargs):
        super().__init__(session, url, *args, **kwargs)
        self._url = url
        self._channel = channel
        self._api = ChzzkAPI(session)

    def refresh_playlist(self):
        log.debug("Refreshing the stream URL to get a new token.")
        datatype, data = self._api.get_live_detail(self._channel)
        if datatype == "error":
            log.error(data)
            return self._url
        media, status, *_ = data
        if status != "OPEN":
            log.error("The stream is unavailable")
            return self._url
        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                media_uri = self._get_media_uri(media_path)
                self._replace_token_from(media_uri)
                log.debug(f"Refreshed the stream URL to {self._url}")
                break

    def _get_media_uri(self, media_path):
        res = self._fetch_variant_playlist(self.session, media_path)
        m3u8 = parse_m3u8(res)
        return m3u8.media[0].uri

    def _get_token_from(self, path):
        return path.split("/")[-2]

    def _replace_token_from(self, media_uri):
        prev_token = self._get_token_from(self._url)
        current_token = self._get_token_from(media_uri)
        self._url = self._url.replace(prev_token, current_token)

    def _should_refresh(self):
        return self._expire is not None and time.time() >= self._expire - \
            self._REFRESH_BEFORE

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

    @classmethod
    def parse_variant_playlist(cls,
                               session: Streamlink,
                               url: str,
                               channel: str,
                               **kwargs) -> Dict[str,
                                                 HLSStream | MuxedHLSStream]:
        stream_name: Optional[str]
        stream: Union["HLSStream", "MuxedHLSStream"]
        streams: Dict[str, Union["HLSStream", "MuxedHLSStream"]] = {}

        request_args = session.http.valid_request_args(**kwargs)
        res = cls._fetch_variant_playlist(session, url, **request_args)

        try:
            multivariant = parse_m3u8(res, parser=cls.__parser__)
        except ValueError as err:
            raise OSError(f"Failed to parse playlist: {err}") from err

        for playlist in multivariant.playlists:
            if playlist.is_iframe:
                continue

            audio_streams = []

            for media in playlist.media:
                if media.type == "AUDIO":
                    audio_streams.append(media)

            if playlist.stream_info.resolution and playlist.stream_info.resolution.height:
                pixels = f"{playlist.stream_info.resolution.height}p"

            stream_name = pixels
            if not stream_name:
                continue

            if audio_streams and FFMPEGMuxer.is_usable(session):
                stream = MuxedChzzkHLSStream(
                    session,
                    video=playlist.uri,
                    audio=[x.uri for x in audio_streams if x.uri],
                    channel=channel,
                    multivariant=multivariant,
                    **kwargs,
                )
            else:
                stream = cls(
                    session,
                    playlist.uri,
                    multivariant=multivariant,
                    channel=channel,
                    **kwargs,
                )

            streams[stream_name] = stream

        return streams


class MuxedChzzkHLSStream(MuxedStream["HLSStream"]):
    __shortname__ = "hls-multi-chzzk"

    def __init__(
        self,
        session: Streamlink,
        video: str,
        audio: Union[str, List[str]],
        channel: str,
        url_master: Optional[str] = None,
        multivariant: Optional[M3U8] = None,
        force_restart: bool = False,
        ffmpeg_options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        tracks = [video]
        maps = ["0:v?", "0:a?"]
        if audio:
            if isinstance(audio, list):
                tracks.extend(audio)
            else:
                tracks.append(audio)
        maps.extend(f"{i}:a" for i in range(1, len(tracks)))
        substreams = [
            ChzzkHLSStream(
                session,
                url,
                channel,
                force_restart=force_restart,
                **kwargs) for url in tracks]
        ffmpeg_options = ffmpeg_options or {}

        super().__init__(
            session,
            *substreams,
            format="mpegts",
            maps=maps,
            **ffmpeg_options)
        self._url_master = url_master
        self.multivariant = multivariant if multivariant and multivariant.is_master else None

    def to_manifest_url(self):
        url = self.multivariant.uri if self.multivariant and self.multivariant.uri else self.url_master

        if url is None:
            return super().to_manifest_url()

        return url


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
                "channel": validate.all(
                    {"channelName": str},
                    validate.get("channelName"),
                ),
                "livePlaybackJson": validate.all(
                    str,
                    validate.parse_json(),
                    {
                        "media":
                            [
                                {
                                    "mediaId": str,
                                    "protocol": str,
                                    "path": validate.url(),
                                }],
                    },
                    validate.get("media"),
                    validate.transform(lambda media: [(m["mediaId"], m["protocol"], m["path"]) for m in media]),
                ),
            },
            validate.union_get(
                "livePlaybackJson",
                "status",
                "liveId",
                "channel",
                "liveCategory",
                "liveTitle",
            ),
        )

    def get_videos(self, video_id):
        return self._query_api(
            self._VIDEOS_URL.format(video_id=video_id),
            {
                "inKey": str,
                "videoId": str,
                "videoTitle": validate.any(str, None),
                "videoCategory": validate.any(str, None),
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
            ),
        )


@pluginmatcher(name="live", pattern=re.compile(
    r"https?://chzzk\.naver\.com/live/(?P<channel_id>[^/?]+)"), )
@pluginmatcher(name="video", pattern=re.compile(
    r"https?://chzzk\.naver\.com/video/(?P<video_id>[^/?]+)"), )
class Chzzk(Plugin):
    _API_VOD_PLAYBACK_URL = "https://apis.naver.com/neonplayer/vodplay/v2/playback/{video_id}?key={in_key}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api = ChzzkAPI(self.session)

    def _get_live(self, channel_id):
        datatype, data = self._api.get_live_detail(channel_id)
        if datatype == "error":
            log.error(data)
            return

        media, status, self.id, self.author, self.category, self.title = data
        if status != "OPEN":
            log.error("The stream is unavailable")
            return
        for media_id, media_protocol, media_path in media:
            if media_protocol == "HLS" and media_id == "HLS":
                return ChzzkHLSStream.parse_variant_playlist(
                    self.session,
                    media_path,
                    channel=channel_id,
                    ffmpeg_options={"copyts": True},
                )

    def _get_video(self, video_id):
        datatype, data = self._api.get_videos(video_id)
        if datatype == "error":
            log.error(data)
            return

        self.id = video_id
        in_key, vod_id, self.author, self.category, self.title = data

        for name, stream in DASHStream.parse_manifest(
            self.session,
            self._API_VOD_PLAYBACK_URL.format(video_id=vod_id, in_key=in_key),
            headers={"Accept": "application/dash+xml"},
        ).items():
            if stream.video_representation.mimeType == "video/mp2t":
                yield name, stream

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_live(self.match["channel_id"])
        elif self.matches["video"]:
            return self._get_video(self.match["video_id"])


__plugin__ = Chzzk
