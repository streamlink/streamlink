"""
$description Global live-streaming and video hosting social platform owned by Amazon.
$url twitch.tv
$type live, vod
$notes See the :ref:`Authentication <cli/plugins/twitch:Authentication>` docs on how to prevent ads.
$notes Read more about :ref:`embedded ads <cli/plugins/twitch:Embedded ads>` here.
$notes :ref:`Low latency streaming <cli/plugins/twitch:Low latency streaming>` is supported.
"""

import argparse
import logging
import re
import sys
from datetime import datetime, timedelta
from random import random
from typing import List, NamedTuple, Optional
from urllib.parse import urlparse

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker, HLSStreamWriter
from streamlink.stream.hls_playlist import ByteRange, DateRange, ExtInf, Key, M3U8, M3U8Parser, Map, load as load_hls_playlist
from streamlink.stream.http import HTTPStream
from streamlink.utils.args import keyvalue
from streamlink.utils.parse import parse_json, parse_qsd
from streamlink.utils.times import hours_minutes_seconds
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)

LOW_LATENCY_MAX_LIVE_EDGE = 2


class TwitchSegment(NamedTuple):
    uri: str
    duration: float
    title: Optional[str]
    key: Optional[Key]
    discontinuity: bool
    byterange: Optional[ByteRange]
    date: Optional[datetime]
    map: Optional[Map]
    ad: bool
    prefetch: bool


# generic namedtuples are unsupported, so just subclass
class TwitchSequence(NamedTuple):
    num: int
    segment: TwitchSegment


class TwitchM3U8(M3U8):
    segments: List[TwitchSegment]  # type: ignore[assignment]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dateranges_ads = []


class TwitchM3U8Parser(M3U8Parser):
    m3u8: TwitchM3U8

    def parse_tag_ext_x_twitch_prefetch(self, value):
        segments = self.m3u8.segments
        if not segments:  # pragma: no cover
            return
        last = segments[-1]
        # Use the average duration of all regular segments for the duration of prefetch segments.
        # This is better than using the duration of the last segment when regular segment durations vary a lot.
        # In low latency mode, the playlist reload time is the duration of the last segment.
        duration = last.duration if last.prefetch else sum(segment.duration for segment in segments) / float(len(segments))
        # Use the last duration for extrapolating the start time of the prefetch segment, which is needed for checking
        # whether it is an ad segment and matches the parsed date ranges or not
        date = last.date + timedelta(seconds=last.duration)
        # Don't pop() the discontinuity state in prefetch segments (at the bottom of the playlist)
        discontinuity = self.state.get("discontinuity", False)
        # Always treat prefetch segments after a discontinuity as ad segments
        ad = discontinuity or self._is_segment_ad(date)
        segment = last._replace(
            uri=self.uri(value),
            duration=duration,
            title=None,
            discontinuity=discontinuity,
            date=date,
            ad=ad,
            prefetch=True,
        )
        segments.append(segment)

    def parse_tag_ext_x_daterange(self, value):
        super().parse_tag_ext_x_daterange(value)
        daterange = self.m3u8.dateranges[-1]
        if self._is_daterange_ad(daterange):
            self.m3u8.dateranges_ads.append(daterange)

    def get_segment(self, uri: str) -> TwitchSegment:  # type: ignore[override]
        extinf: ExtInf = self.state.pop("extinf", None) or ExtInf(0, None)
        date = self.state.pop("date", None)
        ad = self._is_segment_ad(date, extinf.title)

        return TwitchSegment(
            uri=uri,
            duration=extinf.duration,
            title=extinf.title,
            key=self.state.get("key"),
            discontinuity=self.state.pop("discontinuity", False),
            byterange=self.state.pop("byterange", None),
            date=date,
            map=self.state.get("map"),
            ad=ad,
            prefetch=False,
        )

    def _is_segment_ad(self, date: datetime, title: Optional[str] = None) -> bool:
        return (
            title is not None and "Amazon" in title
            or any(self.m3u8.is_date_in_daterange(date, daterange) for daterange in self.m3u8.dateranges_ads)
        )

    @staticmethod
    def _is_daterange_ad(daterange: DateRange) -> bool:
        return (
            daterange.classname == "twitch-stitched-ad"
            or str(daterange.id or "").startswith("stitched-ad-")
            or any(attr_key.startswith("X-TV-TWITCH-AD-") for attr_key in daterange.x.keys())
        )


class TwitchHLSStreamWorker(HLSStreamWorker):
    reader: "TwitchHLSStreamReader"
    writer: "TwitchHLSStreamWriter"
    stream: "TwitchHLSStream"

    def __init__(self, reader, *args, **kwargs):
        self.had_content = False
        super().__init__(reader, *args, **kwargs)

    def _reload_playlist(self, *args):
        return load_hls_playlist(*args, parser=TwitchM3U8Parser, m3u8=TwitchM3U8)

    def _playlist_reload_time(self, playlist: TwitchM3U8, sequences: List[TwitchSequence]):  # type: ignore[override]
        if self.stream.low_latency and sequences:
            return sequences[-1].segment.duration

        return super()._playlist_reload_time(playlist, sequences)  # type: ignore[arg-type]

    def process_sequences(self, playlist: TwitchM3U8, sequences: List[TwitchSequence]):  # type: ignore[override]
        # ignore prefetch segments if not LL streaming
        if not self.stream.low_latency:
            sequences = [seq for seq in sequences if not seq.segment.prefetch]

        # check for sequences with real content
        if not self.had_content:
            self.had_content = next((True for seq in sequences if not seq.segment.ad), False)

            # When filtering ads, to check whether it's a LL stream, we need to wait for the real content to show up,
            # since playlists with only ad segments don't contain prefetch segments
            if (
                self.stream.low_latency
                and self.had_content
                and not next((True for seq in sequences if seq.segment.prefetch), False)
            ):
                log.info("This is not a low latency stream")

        # show pre-roll ads message only on the first playlist containing ads
        if self.stream.disable_ads and self.playlist_sequence == -1 and not self.had_content:
            log.info("Waiting for pre-roll ads to finish, be patient")

        return super().process_sequences(playlist, sequences)  # type: ignore[arg-type]


class TwitchHLSStreamWriter(HLSStreamWriter):
    reader: "TwitchHLSStreamReader"
    stream: "TwitchHLSStream"

    def should_filter_sequence(self, sequence: TwitchSequence):  # type: ignore[override]
        return self.stream.disable_ads and sequence.segment.ad


class TwitchHLSStreamReader(HLSStreamReader):
    __worker__ = TwitchHLSStreamWorker
    __writer__ = TwitchHLSStreamWriter

    worker: "TwitchHLSStreamWorker"
    writer: "TwitchHLSStreamWriter"
    stream: "TwitchHLSStream"

    def __init__(self, stream: "TwitchHLSStream"):
        if stream.disable_ads:
            log.info("Will skip ad segments")
        if stream.low_latency:
            live_edge = max(1, min(LOW_LATENCY_MAX_LIVE_EDGE, stream.session.options.get("hls-live-edge")))
            stream.session.options.set("hls-live-edge", live_edge)
            stream.session.options.set("hls-segment-stream-data", True)
            log.info(f"Low latency streaming (HLS live edge: {live_edge})")
        super().__init__(stream)


class TwitchHLSStream(HLSStream):
    __reader__ = TwitchHLSStreamReader

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disable_ads = self.session.get_plugin_option("twitch", "disable-ads")
        self.low_latency = self.session.get_plugin_option("twitch", "low-latency")


class UsherService:
    def __init__(self, session):
        self.session = session

    def _create_url(self, endpoint, **extra_params):
        url = f"https://usher.ttvnw.net{endpoint}"
        params = {
            "player": "twitchweb",
            "p": int(random() * 999999),
            "type": "any",
            "allow_source": "true",
            "allow_audio_only": "true",
            "allow_spectre": "false",
        }
        params.update(extra_params)

        req = self.session.http.prepare_new_request(url=url, params=params)

        return req.url

    def channel(self, channel, **extra_params):
        try:
            extra_params_debug = validate.Schema(
                validate.get("token"),
                validate.parse_json(),
                {
                    "adblock": bool,
                    "geoblock_reason": str,
                    "hide_ads": bool,
                    "server_ads": bool,
                    "show_ads": bool,
                }
            ).validate(extra_params)
            log.debug(f"{extra_params_debug!r}")
        except PluginError:
            pass
        return self._create_url(f"/api/channel/hls/{channel}.m3u8", **extra_params)

    def video(self, video_id, **extra_params):
        return self._create_url(f"/vod/{video_id}", **extra_params)


class TwitchAPI:
    CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    def __init__(self, session):
        self.session = session
        self.headers = {
            "Client-ID": self.CLIENT_ID,
        }
        self.headers.update(**dict(session.get_plugin_option("twitch", "api-header") or []))
        self.access_token_params = dict(session.get_plugin_option("twitch", "access-token-param") or [])
        self.access_token_params.setdefault("playerType", "embed")

    def call(self, data, schema=None, **kwargs):
        res = self.session.http.post(
            "https://gql.twitch.tv/gql",
            json=data,
            headers={**self.headers, **kwargs.pop("headers", {})},
            **kwargs,
        )

        return self.session.http.json(res, schema=schema)

    @staticmethod
    def _gql_persisted_query(operationname, sha256hash, **variables):
        return {
            "operationName": operationname,
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": sha256hash
                }
            },
            "variables": dict(**variables)
        }

    @staticmethod
    def parse_token(tokenstr):
        return parse_json(tokenstr, schema=validate.Schema(
            {"chansub": {"restricted_bitrates": validate.all(
                [str],
                validate.filter(lambda n: not re.match(r"(.+_)?archives|live|chunked", n))
            )}},
            validate.get(("chansub", "restricted_bitrates"))
        ))

    # GraphQL API calls

    def metadata_video(self, video_id):
        query = self._gql_persisted_query(
            "VideoMetadata",
            "cb3b1eb2f2d2b2f65b8389ba446ec521d76c3aa44f5424a1b1d235fe21eb4806",
            channelLogin="",  # parameter can be empty
            videoID=video_id
        )

        return self.call(query, schema=validate.Schema(
            {"data": {"video": {
                "id": str,
                "owner": {
                    "displayName": str
                },
                "title": str,
                "game": {
                    "displayName": str
                }
            }}},
            validate.get(("data", "video")),
            validate.union_get(
                "id",
                ("owner", "displayName"),
                ("game", "displayName"),
                "title"
            )
        ))

    def metadata_channel(self, channel):
        queries = [
            self._gql_persisted_query(
                "ChannelShell",
                "c3ea5a669ec074a58df5c11ce3c27093fa38534c94286dc14b68a25d5adcbf55",
                login=channel,
                lcpVideosEnabled=False
            ),
            self._gql_persisted_query(
                "StreamMetadata",
                "059c4653b788f5bdb2f5a2d2a24b0ddc3831a15079001a3d927556a96fb0517f",
                channelLogin=channel
            )
        ]

        return self.call(queries, schema=validate.Schema(
            [
                validate.all(
                    {"data": {"userOrError": {
                        "displayName": str
                    }}}
                ),
                validate.all(
                    {"data": {"user": {
                        "lastBroadcast": {
                            "title": str
                        },
                        "stream": {
                            "id": str,
                            "game": {
                                "name": str
                            }
                        }
                    }}}
                )
            ],
            validate.union_get(
                (1, "data", "user", "stream", "id"),
                (0, "data", "userOrError", "displayName"),
                (1, "data", "user", "stream", "game", "name"),
                (1, "data", "user", "lastBroadcast", "title")
            )
        ))

    def metadata_clips(self, clipname):
        queries = [
            self._gql_persisted_query(
                "ClipsView",
                "4480c1dcc2494a17bb6ef64b94a5213a956afb8a45fe314c66b0d04079a93a8f",
                slug=clipname
            ),
            self._gql_persisted_query(
                "ClipsTitle",
                "f6cca7f2fdfbfc2cecea0c88452500dae569191e58a265f97711f8f2a838f5b4",
                slug=clipname
            )
        ]

        return self.call(queries, schema=validate.Schema(
            [
                validate.all(
                    {"data": {"clip": {
                        "id": str,
                        "broadcaster": {"displayName": str},
                        "game": {"name": str}
                    }}},
                    validate.get(("data", "clip"))
                ),
                validate.all(
                    {"data": {"clip": {"title": str}}},
                    validate.get(("data", "clip"))
                )
            ],
            validate.union_get(
                (0, "id"),
                (0, "broadcaster", "displayName"),
                (0, "game", "name"),
                (1, "title")
            )
        ))

    def access_token(self, is_live, channel_or_vod):
        query = self._gql_persisted_query(
            "PlaybackAccessToken",
            "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712",
            isLive=is_live,
            login=channel_or_vod if is_live else "",
            isVod=not is_live,
            vodID=channel_or_vod if not is_live else "",
            **self.access_token_params,
        )
        subschema = validate.none_or_all(
            {
                "value": str,
                "signature": str,
            },
            validate.union_get("signature", "value"),
        )

        return self.call(query, acceptable_status=(200, 400, 401, 403), schema=validate.Schema(
            validate.any(
                validate.all(
                    {"error": str, "message": str},
                    validate.union_get("error", "message"),
                    validate.transform(lambda data: ("error", *data)),
                ),
                validate.all(
                    {
                        "data": validate.any(
                            validate.all(
                                {"streamPlaybackAccessToken": subschema},
                                validate.get("streamPlaybackAccessToken"),
                            ),
                            validate.all(
                                {"videoPlaybackAccessToken": subschema},
                                validate.get("videoPlaybackAccessToken"),
                            ),
                        ),
                    },
                    validate.get("data"),
                    validate.transform(lambda data: ("token", *data)),
                ),
            ),
        ))

    def clips(self, clipname):
        query = self._gql_persisted_query(
            "VideoAccessToken_Clip",
            "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11",
            slug=clipname
        )

        return self.call(query, schema=validate.Schema(
            {"data": {"clip": {
                "playbackAccessToken": {
                    "signature": str,
                    "value": str
                },
                "videoQualities": [validate.all(
                    {
                        "frameRate": validate.transform(int),
                        "quality": str,
                        "sourceURL": validate.url()
                    },
                    validate.transform(lambda q: (
                        f"{q['quality']}p{q['frameRate']}",
                        q["sourceURL"]
                    ))
                )]
            }}},
            validate.get(("data", "clip")),
            validate.union_get(
                ("playbackAccessToken", "signature"),
                ("playbackAccessToken", "value"),
                "videoQualities"
            )
        ))

    def stream_metadata(self, channel):
        query = self._gql_persisted_query(
            "StreamMetadata",
            "1c719a40e481453e5c48d9bb585d971b8b372f8ebb105b17076722264dfa5b3e",
            channelLogin=channel
        )

        return self.call(query, schema=validate.Schema(
            {"data": {"user": {"stream": {"type": str}}}},
            validate.get(("data", "user", "stream"))
        ))


@pluginmatcher(re.compile(r"""
    https?://(?:(?P<subdomain>[\w-]+)\.)?twitch\.tv/
    (?:
        videos/(?P<videos_id>\d+)
        |
        (?P<channel>[^/?]+)
        (?:
            /v(?:ideo)?/(?P<video_id>\d+)
            |
            /clip/(?P<clip_name>[^/?]+)
        )?
    )
""", re.VERBOSE))
@pluginargument(
    "disable-ads",
    action="store_true",
    help="""
        Skip embedded advertisement segments at the beginning or during a stream.
        Will cause these segments to be missing from the output.
    """,
)
@pluginargument(
    "disable-hosting",
    action="store_true",
    help=argparse.SUPPRESS,
)
@pluginargument(
    "disable-reruns",
    action="store_true",
    help="Do not open the stream if the target channel is currently broadcasting a rerun.",
)
@pluginargument(
    "low-latency",
    action="store_true",
    help=f"""
        Enables low latency streaming by prefetching HLS segments.
        Sets --hls-segment-stream-data to true and --hls-live-edge to `{LOW_LATENCY_MAX_LIVE_EDGE}`, if it is higher.
        Reducing --hls-live-edge to `1` will result in the lowest latency possible, but will most likely cause buffering.

        In order to achieve true low latency streaming during playback, the player's caching/buffering settings will
        need to be adjusted and reduced to a value as low as possible, but still high enough to not cause any buffering.
        This depends on the stream's bitrate and the quality of the connection to Twitch's servers. Please refer to the
        player's own documentation for the required configuration. Player parameters can be set via --player-args.

        Note: Low latency streams have to be enabled by the broadcasters on Twitch themselves.
        Regular streams can cause buffering issues with this option enabled due to the reduced --hls-live-edge value.
    """,
)
@pluginargument(
    "api-header",
    metavar="KEY=VALUE",
    type=keyvalue,
    action="append",
    help="""
        A header to add to each Twitch API HTTP request.

        Can be repeated to add multiple headers.

        Useful for adding authentication data that can prevent ads. See the plugin-specific documentation for more information.
    """,
)
@pluginargument(
    "access-token-param",
    metavar="KEY=VALUE",
    type=keyvalue,
    action="append",
    help="""
        A parameter to add to the API request for acquiring the streaming access token.

        Can be repeated to add multiple parameters.
    """,
)
class Twitch(Plugin):
    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return sys.maxsize, stream
        return super().stream_weight(stream)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        match = self.match.groupdict()
        parsed = urlparse(self.url)
        self.params = parse_qsd(parsed.query)
        self.subdomain = match.get("subdomain")
        self.video_id = None
        self.channel = None
        self.clip_name = None
        self._checked_metadata = False

        if self.subdomain == "player":
            # pop-out player
            if self.params.get("video"):
                self.video_id = self.params["video"]
            self.channel = self.params.get("channel")
        elif self.subdomain == "clips":
            # clip share URL
            self.clip_name = match.get("channel")
        else:
            self.channel = match.get("channel") and match.get("channel").lower()
            self.video_id = match.get("video_id") or match.get("videos_id")
            self.clip_name = match.get("clip_name")

        self.api = TwitchAPI(session=self.session)
        self.usher = UsherService(session=self.session)

        def method_factory(parent_method):
            def inner():
                if not self._checked_metadata:
                    self._checked_metadata = True
                    self._get_metadata()
                return parent_method()
            return inner

        parent = super()
        for metadata in "id", "author", "category", "title":
            method = f"get_{metadata}"
            setattr(self, method, method_factory(getattr(parent, method)))

    def _get_metadata(self):
        try:
            if self.video_id:
                data = self.api.metadata_video(self.video_id)
            elif self.clip_name:
                data = self.api.metadata_clips(self.clip_name)
            elif self.channel:
                data = self.api.metadata_channel(self.channel)
            else:  # pragma: no cover
                return
            self.id, self.author, self.category, self.title = data
        except (PluginError, TypeError):
            pass

    def _access_token(self, is_live, channel_or_vod):
        try:
            response, *data = self.api.access_token(is_live, channel_or_vod)
            if response != "token":
                error, message = data
                log.error(f"{error or 'Error'}: {message or 'Unknown error'}")
                raise PluginError
            sig, token = data
        except (PluginError, TypeError):
            raise NoStreamsError(self.url)

        try:
            restricted_bitrates = self.api.parse_token(token)
        except PluginError:
            restricted_bitrates = []

        return sig, token, restricted_bitrates

    def _check_for_rerun(self):
        if not self.options.get("disable_reruns"):
            return False

        try:
            stream = self.api.stream_metadata(self.channel)
            if stream["type"] != "live":
                log.info("Reruns were disabled by command line option")
                return True
        except (PluginError, TypeError):
            pass

        return False

    def _get_hls_streams_live(self):
        if self._check_for_rerun():
            return

        # only get the token once the channel has been resolved
        log.debug(f"Getting live HLS streams for {self.channel}")
        self.session.http.headers.update({
            "referer": "https://player.twitch.tv",
            "origin": "https://player.twitch.tv",
        })
        sig, token, restricted_bitrates = self._access_token(True, self.channel)
        url = self.usher.channel(self.channel, sig=sig, token=token, fast_bread=True)

        return self._get_hls_streams(url, restricted_bitrates)

    def _get_hls_streams_video(self):
        log.debug(f"Getting HLS streams for video ID {self.video_id}")
        sig, token, restricted_bitrates = self._access_token(False, self.video_id)
        url = self.usher.video(self.video_id, nauthsig=sig, nauth=token)

        # If the stream is a VOD that is still being recorded, the stream should start at the beginning of the recording
        return self._get_hls_streams(url, restricted_bitrates, force_restart=True)

    def _get_hls_streams(self, url, restricted_bitrates, **extra_params):
        time_offset = self.params.get("t", 0)
        if time_offset:
            try:
                time_offset = hours_minutes_seconds(time_offset)
            except ValueError:
                time_offset = 0

        try:
            streams = TwitchHLSStream.parse_variant_playlist(self.session, url, start_offset=time_offset, **extra_params)
        except OSError as err:
            err = str(err)
            if "404 Client Error" in err or "Failed to parse playlist" in err:
                return
            else:
                raise PluginError(err)

        for name in restricted_bitrates:
            if name not in streams:
                log.warning(f"The quality '{name}' is not available since it requires a subscription.")

        return streams

    def _get_clips(self):
        try:
            sig, token, streams = self.api.clips(self.clip_name)
        except (PluginError, TypeError):
            return

        for quality, stream in streams:
            yield quality, HTTPStream(self.session, update_qsd(stream, {"sig": sig, "token": token}))

    def _get_streams(self):
        if self.video_id:
            return self._get_hls_streams_video()
        elif self.clip_name:
            return self._get_clips()
        elif self.channel:
            return self._get_hls_streams_live()


__plugin__ = Twitch
