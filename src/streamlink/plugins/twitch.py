"""
$description Global live-streaming and video hosting social platform owned by Amazon.
$url twitch.tv
$type live, vod
$webbrowser Required for getting a new :ref:`client-integrity token <cli/plugins/twitch:Client-integrity token>`.
$metadata id
$metadata author
$metadata category
$metadata title
$notes See the :ref:`Authentication <cli/plugins/twitch:Authentication>` docs on how to prevent ads.
$notes Read more about :ref:`embedded ads <cli/plugins/twitch:Embedded ads>` here.
$notes :ref:`Low latency streaming <cli/plugins/twitch:Low latency streaming>` is supported.
$notes Acquires a :ref:`client-integrity token <cli/plugins/twitch:Client-integrity token>` on streaming access token failure.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
import sys
from collections import deque
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, replace as dataclass_replace
from datetime import datetime, timedelta
from json import dumps as json_dumps
from random import random
from typing import ClassVar
from urllib.parse import urlparse

from requests.exceptions import HTTPError

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.session import Streamlink
from streamlink.stream.hls import (
    M3U8,
    DateRange,
    HLSPlaylist,
    HLSSegment,
    HLSStream,
    HLSStreamReader,
    HLSStreamWorker,
    HLSStreamWriter,
    M3U8Parser,
    parse_tag,
)
from streamlink.stream.http import HTTPStream
from streamlink.utils.parse import parse_json, parse_qsd
from streamlink.utils.random import CHOICES_ALPHA_NUM, random_token
from streamlink.utils.times import fromtimestamp, hours_minutes_seconds_float
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)

LOW_LATENCY_MAX_LIVE_EDGE = 2


@dataclass
class TwitchHLSSegment(HLSSegment):
    ad: bool
    prefetch: bool


class TwitchM3U8(M3U8[TwitchHLSSegment, HLSPlaylist]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dateranges_ads: list[DateRange] = []


class TwitchM3U8Parser(M3U8Parser[TwitchM3U8, TwitchHLSSegment, HLSPlaylist]):
    __m3u8__: ClassVar[type[TwitchM3U8]] = TwitchM3U8
    __segment__: ClassVar[type[TwitchHLSSegment]] = TwitchHLSSegment

    @parse_tag("EXT-X-TWITCH-LIVE-SEQUENCE")
    def parse_ext_x_twitch_live_sequence(self, value):
        # Unset discontinuity state if the previous segment was not an ad,
        # as the following segment won't be an ad
        if self.m3u8.segments and not self.m3u8.segments[-1].ad:
            self._discontinuity = False

    @parse_tag("EXT-X-TWITCH-PREFETCH")
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

        # Always treat prefetch segments after a discontinuity as ad segments
        # (discontinuity tag inserted after last regular segment)
        # Don't reset discontinuity state: the date extrapolation might be inaccurate,
        # so all following prefetch segments should be considered an ad after a discontinuity
        ad = self._discontinuity or self._is_segment_ad(date)

        # Since we don't reset the discontinuity state in prefetch segments for the purpose of ad detection,
        # set the prefetch segment's discontinuity attribute based on ad transitions
        discontinuity = ad != last.ad

        segment = dataclass_replace(
            last,
            uri=self.uri(value),
            duration=duration,
            title=None,
            discontinuity=discontinuity,
            date=date,
            ad=ad,
            prefetch=True,
        )
        segments.append(segment)

    @parse_tag("EXT-X-DATERANGE")
    def parse_tag_ext_x_daterange(self, value):
        super().parse_tag_ext_x_daterange(value)
        daterange = self.m3u8.dateranges[-1]
        if self._is_daterange_ad(daterange):
            self.m3u8.dateranges_ads.append(daterange)

    def get_segment(self, uri: str, **data) -> TwitchHLSSegment:
        ad = self._is_segment_ad(self._date, self._extinf.title if self._extinf else None)
        segment: TwitchHLSSegment = super().get_segment(uri, ad=ad, prefetch=False)  # type: ignore[assignment]

        # Special case where Twitch incorrectly inserts discontinuity tags between segments of the live content
        if (
            segment.discontinuity
            and not segment.ad
            and self.m3u8.segments
            and not self.m3u8.segments[-1].ad
        ):  # fmt: skip
            segment.discontinuity = False

        return segment

    def _is_segment_ad(self, date: datetime | None, title: str | None = None) -> bool:
        return (
            title is not None and "Amazon" in title
            or any(self.m3u8.is_date_in_daterange(date, daterange) for daterange in self.m3u8.dateranges_ads)
        )  # fmt: skip

    @staticmethod
    def _is_daterange_ad(daterange: DateRange) -> bool:
        return (
            daterange.classname == "twitch-stitched-ad"
            or str(daterange.id or "").startswith("stitched-ad-")
            or any(attr_key.startswith("X-TV-TWITCH-AD-") for attr_key in daterange.x.keys())
        )


class TwitchHLSStreamWorker(HLSStreamWorker):
    reader: TwitchHLSStreamReader
    writer: TwitchHLSStreamWriter
    stream: TwitchHLSStream

    def __init__(self, reader, *args, **kwargs) -> None:
        self.had_content: bool = False
        self.logged_ads: deque[str] = deque(maxlen=10)
        super().__init__(reader, *args, **kwargs)

    def _playlist_reload_time(self, playlist: TwitchM3U8):  # type: ignore[override]
        if self.stream.low_latency and playlist.segments:
            return playlist.segments[-1].duration

        return super()._playlist_reload_time(playlist)

    def process_segments(self, playlist: TwitchM3U8):  # type: ignore[override]
        # ignore prefetch segments if not LL streaming
        if not self.stream.low_latency:
            playlist.segments = [segment for segment in playlist.segments if not segment.prefetch]

        # check for sequences with real content
        if not self.had_content:
            self.had_content = next((True for segment in playlist.segments if not segment.ad), False)

            # When filtering ads, to check whether it's a LL stream, we need to wait for the real content to show up,
            # since playlists with only ad segments don't contain prefetch segments
            if (
                self.stream.low_latency
                and self.had_content
                and not next((True for segment in playlist.segments if segment.prefetch), False)
            ):
                log.info("This is not a low latency stream")

        # show pre-roll ads message only on the first playlist containing ads
        if self.stream.disable_ads and self.playlist_sequence == -1 and not self.had_content:
            log.info("Waiting for pre-roll ads to finish, be patient")

        # log the duration of whole advertisement breaks
        for daterange_ads in playlist.dateranges_ads:
            if not daterange_ads.duration:  # pragma: no cover
                continue

            ads_id: str | None = (
                daterange_ads.x.get("X-TV-TWITCH-AD-COMMERCIAL-ID")
                or daterange_ads.x.get("X-TV-TWITCH-AD-ROLL-TYPE")
            )  # fmt: skip
            if not ads_id or ads_id in self.logged_ads:
                continue
            self.logged_ads.append(ads_id)

            # use Twitch's own ads duration metadata if available
            try:
                duration = math.ceil(float(daterange_ads.x.get("X-TV-TWITCH-AD-POD-FILLED-DURATION", "")))
            except ValueError:
                duration = math.ceil(daterange_ads.duration.total_seconds())

            log.info(f"Detected advertisement break of {duration} second{'s' if duration != 1 else ''}")

        return super().process_segments(playlist)


class TwitchHLSStreamWriter(HLSStreamWriter):
    reader: TwitchHLSStreamReader
    stream: TwitchHLSStream

    def should_filter_segment(self, segment: TwitchHLSSegment) -> bool:  # type: ignore[override]
        return self.stream.disable_ads and segment.ad


class TwitchHLSStreamReader(HLSStreamReader):
    __worker__ = TwitchHLSStreamWorker
    __writer__ = TwitchHLSStreamWriter

    worker: TwitchHLSStreamWorker
    writer: TwitchHLSStreamWriter
    stream: TwitchHLSStream

    def __init__(self, stream: TwitchHLSStream):
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
    __parser__ = TwitchM3U8Parser

    def __init__(self, *args, disable_ads: bool = False, low_latency: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.disable_ads = disable_ads
        self.low_latency = low_latency


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

    def channel(self, channel: str, **extra_params) -> str:
        with suppress(PluginError):
            extra_params_debug = validate.Schema(
                validate.get("token"),
                validate.parse_json(),
                {
                    "adblock": bool,
                    "geoblock_reason": str,
                    "hide_ads": bool,
                    "server_ads": bool,
                    "show_ads": bool,
                },
            ).validate(extra_params)
            log.debug(f"{extra_params_debug!r}")

        return self._create_url(f"/api/channel/hls/{channel.lower()}.m3u8", **extra_params)

    def video(self, video_id: str, **extra_params) -> str:
        return self._create_url(f"/vod/{video_id}", **extra_params)


class TwitchAPI:
    CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    def __init__(self, session, api_header=None, access_token_param=None):
        self.session = session
        self.headers = {
            "Client-ID": self.CLIENT_ID,
        }
        self.headers.update(**dict(api_header or []))
        self.access_token_params = dict(access_token_param or [])
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
                    "sha256Hash": sha256hash,
                },
            },
            "variables": dict(**variables),
        }

    @staticmethod
    def parse_token(tokenstr):
        return parse_json(
            tokenstr,
            schema=validate.Schema(
                {
                    "chansub": {
                        "restricted_bitrates": validate.all(
                            [str],
                            validate.filter(lambda n: not re.match(r"(.+_)?archives|live|chunked", n)),
                        ),
                    },
                },
                validate.get(("chansub", "restricted_bitrates")),
            ),
        )

    # GraphQL API calls

    def metadata_video(self, video_id):
        query = self._gql_persisted_query(
            "VideoMetadata",
            "cb3b1eb2f2d2b2f65b8389ba446ec521d76c3aa44f5424a1b1d235fe21eb4806",
            channelLogin="",  # parameter can be empty
            videoID=video_id,
        )

        return self.call(
            query,
            schema=validate.Schema(
                {
                    "data": {
                        "video": {
                            "id": str,
                            "owner": {
                                "displayName": str,
                            },
                            "title": str,
                            "game": {
                                "displayName": str,
                            },
                        },
                    },
                },
                validate.get(("data", "video")),
                validate.union_get(
                    "id",
                    ("owner", "displayName"),
                    ("game", "displayName"),
                    "title",
                ),
            ),
        )

    def metadata_channel(self, channel):
        queries = [
            self._gql_persisted_query(
                "ChannelShell",
                "c3ea5a669ec074a58df5c11ce3c27093fa38534c94286dc14b68a25d5adcbf55",
                login=channel,
                lcpVideosEnabled=False,
            ),
            self._gql_persisted_query(
                "StreamMetadata",
                "059c4653b788f5bdb2f5a2d2a24b0ddc3831a15079001a3d927556a96fb0517f",
                channelLogin=channel,
            ),
        ]

        return self.call(
            queries,
            schema=validate.Schema(
                [
                    validate.all(
                        {
                            "data": {
                                "userOrError": {
                                    "displayName": str,
                                },
                            },
                        },
                    ),
                    validate.all(
                        {
                            "data": {
                                "user": {
                                    "lastBroadcast": {
                                        "title": str,
                                    },
                                    "stream": {
                                        "id": str,
                                        "game": {
                                            "name": str,
                                        },
                                    },
                                },
                            },
                        },
                    ),
                ],
                validate.union_get(
                    (1, "data", "user", "stream", "id"),
                    (0, "data", "userOrError", "displayName"),
                    (1, "data", "user", "stream", "game", "name"),
                    (1, "data", "user", "lastBroadcast", "title"),
                ),
            ),
        )

    def metadata_clips(self, clipname):
        queries = [
            self._gql_persisted_query(
                "ClipsView",
                "4480c1dcc2494a17bb6ef64b94a5213a956afb8a45fe314c66b0d04079a93a8f",
                slug=clipname,
            ),
            self._gql_persisted_query(
                "ClipsTitle",
                "f6cca7f2fdfbfc2cecea0c88452500dae569191e58a265f97711f8f2a838f5b4",
                slug=clipname,
            ),
        ]

        return self.call(
            queries,
            schema=validate.Schema(
                [
                    validate.all(
                        {
                            "data": {
                                "clip": {
                                    "id": str,
                                    "broadcaster": {"displayName": str},
                                    "game": {"name": str},
                                },
                            },
                        },
                        validate.get(("data", "clip")),
                    ),
                    validate.all(
                        {"data": {"clip": {"title": str}}},
                        validate.get(("data", "clip")),
                    ),
                ],
                validate.union_get(
                    (0, "id"),
                    (0, "broadcaster", "displayName"),
                    (0, "game", "name"),
                    (1, "title"),
                ),
            ),
        )

    def access_token(self, is_live, channel_or_vod, client_integrity: tuple[str, str] | None = None):
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

        headers = {}
        if client_integrity:
            headers["Device-Id"], headers["Client-Integrity"] = client_integrity

        return self.call(
            query,
            acceptable_status=(200, 400, 401, 403),
            headers=headers,
            schema=validate.Schema(
                validate.any(
                    validate.all(
                        {"errors": [{"message": str}]},
                        validate.get(("errors", 0, "message")),
                        validate.transform(lambda data: ("error", None, data)),
                    ),
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
                        validate.transform(lambda data: ("token", *data) if data is not None else ("token", None, None)),
                    ),
                ),
            ),
        )

    def clips(self, clipname):
        query = self._gql_persisted_query(
            "VideoAccessToken_Clip",
            "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11",
            slug=clipname,
        )

        return self.call(
            query,
            schema=validate.Schema(
                {
                    "data": {
                        "clip": {
                            "playbackAccessToken": {
                                "signature": str,
                                "value": str,
                            },
                            "videoQualities": [
                                validate.all(
                                    {
                                        "frameRate": validate.transform(int),
                                        "quality": str,
                                        "sourceURL": validate.url(),
                                    },
                                    validate.transform(
                                        lambda q: (
                                            f"{q['quality']}p{q['frameRate']}",
                                            q["sourceURL"],
                                        ),
                                    ),
                                ),
                            ],
                        },
                    },
                },
                validate.get(("data", "clip")),
                validate.union_get(
                    ("playbackAccessToken", "signature"),
                    ("playbackAccessToken", "value"),
                    "videoQualities",
                ),
            ),
        )


class TwitchClientIntegrity:
    URL_P_SCRIPT = "https://k.twitchcdn.net/149e9513-01fa-4fb0-aad4-566afd725d1b/2d206a39-8ed7-437e-a3be-862e0f06eea3/p.js"

    # language=javascript
    JS_INTEGRITY_TOKEN = """
    // noinspection JSIgnoredPromiseFromCall
    new Promise((resolve, reject) => {
        function configureKPSDK() {
            // noinspection JSUnresolvedVariable,JSUnresolvedFunction
            window.KPSDK.configure([{
                "protocol": "https:",
                "method": "POST",
                "domain": "gql.twitch.tv",
                "path": "/integrity"
            }]);
        }

        async function fetchIntegrity() {
            // noinspection JSUnresolvedReference
            const headers = Object.assign(HEADERS, {"x-device-id": "DEVICE_ID"});
            // window.fetch gets overridden and the patched function needs to be used
            const resp = await window.fetch("https://gql.twitch.tv/integrity", {
                "headers": headers,
                "body": null,
                "method": "POST",
                "mode": "cors",
                "credentials": "omit"
            });

            if (resp.status !== 200) {
                throw new Error(`Unexpected integrity response status code ${resp.status}`);
            }

            return JSON.stringify(await resp.json());
        }

        document.addEventListener("kpsdk-load", configureKPSDK, {once: true});
        document.addEventListener("kpsdk-ready", () => fetchIntegrity().then(resolve, reject), {once: true});

        const script = document.createElement("script");
        script.addEventListener("error", reject);
        script.src = "SCRIPT_SOURCE";
        document.body.appendChild(script);
    });
    """

    @classmethod
    def acquire(
        cls,
        session: Streamlink,
        channel: str,
        headers: Mapping[str, str],
        device_id: str,
    ) -> tuple[str, int] | None:
        from streamlink.compat import BaseExceptionGroup  # noqa: PLC0415
        from streamlink.webbrowser.cdp import CDPClient, CDPClientSession, devtools  # noqa: PLC0415

        url = f"https://www.twitch.tv/{channel}"
        js_get_integrity_token = cls.JS_INTEGRITY_TOKEN \
            .replace("SCRIPT_SOURCE", cls.URL_P_SCRIPT) \
            .replace("HEADERS", json_dumps(headers)) \
            .replace("DEVICE_ID", device_id)  # fmt: skip
        eval_timeout = session.get_option("webbrowser-timeout")
        # noinspection PyUnusedLocal
        client_integrity: str | None = None

        async def on_main(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
            async with client_session.alter_request(request) as cm:
                cm.body = "<!doctype html>"

        async def acquire_client_integrity_token(client: CDPClient):
            client_session: CDPClientSession
            async with client.session() as client_session:
                client_session.add_request_handler(on_main, url_pattern=url, on_request=True)
                async with client_session.navigate(url) as frame_id:
                    await client_session.loaded(frame_id)
                    return await client_session.evaluate(js_get_integrity_token, timeout=eval_timeout)

        try:
            client_integrity = CDPClient.launch(session, acquire_client_integrity_token)
        except BaseExceptionGroup:
            log.exception("Failed acquiring client integrity token")
        except Exception as err:
            log.error(err)

        if not client_integrity:
            return None

        schema = validate.Schema(
            validate.parse_json(),
            {"token": str, "expiration": int},
            validate.union_get("token", "expiration"),
        )
        token, expiration = schema.validate(client_integrity)

        return token, expiration / 1000


@pluginmatcher(
    name="player",
    pattern=re.compile(
        r"https?://player\.twitch\.tv/\?.+",
    ),
)
@pluginmatcher(
    name="clip",
    pattern=re.compile(
        r"https?://(?:clips\.twitch\.tv|(?:[\w-]+\.)?twitch\.tv/(?:[\w-]+/)?clip)/(?P<clip_id>[^/?]+)",
    ),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(
        r"https?://(?:[\w-]+\.)?twitch\.tv/(?:[\w-]+/)?v(?:ideos?)?/(?P<video_id>\d+)",
    ),
)
@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:(?!clips\.)[\w-]+\.)?twitch\.tv/(?P<channel>(?!v(?:ideos?)?/|clip/)[^/?]+)/?(?:\?|$)",
    ),
)
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
    help=argparse.SUPPRESS,
)
@pluginargument(
    "low-latency",
    action="store_true",
    help="""
        Enables low latency streaming by prefetching HLS segments.
        Sets --hls-segment-stream-data to true and --hls-live-edge to 2, if it is higher.
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
    type="keyvalue",
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
    type="keyvalue",
    action="append",
    help="""
        A parameter to add to the API request for acquiring the streaming access token.

        Can be repeated to add multiple parameters.
    """,
)
@pluginargument(
    "force-client-integrity",
    action="store_true",
    help="Don't attempt requesting the streaming access token without a client-integrity token.",
)
@pluginargument(
    "purge-client-integrity",
    action="store_true",
    help="Purge cached Twitch client-integrity token and acquire a new one.",
)
class Twitch(Plugin):
    _CACHE_KEY_CLIENT_INTEGRITY = "client-integrity"

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return sys.maxsize, stream
        return super().stream_weight(stream)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        params = parse_qsd(urlparse(self.url).query)

        self.channel = self.match["channel"] if self.matches["live"] else None
        self.video_id = self.match["video_id"] if self.matches["vod"] else None
        self.clip_id = self.match["clip_id"] if self.matches["clip"] else None

        if self.matches["player"]:
            self.channel = params.get("channel")
            self.video_id = params.get("video")

        try:
            self.time_offset = hours_minutes_seconds_float(params.get("t", "0"))
        except ValueError:
            self.time_offset = 0

        self.api = TwitchAPI(
            session=self.session,
            api_header=self.get_option("api-header"),
            access_token_param=self.get_option("access-token-param"),
        )
        self.usher = UsherService(session=self.session)

        self._checked_metadata = False

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
            elif self.clip_id:
                data = self.api.metadata_clips(self.clip_id)
            elif self.channel:
                data = self.api.metadata_channel(self.channel)
            else:  # pragma: no cover
                return
            self.id, self.author, self.category, self.title = data
        except (PluginError, TypeError):
            pass

    def _client_integrity_token(self, channel: str) -> tuple[str, str] | None:
        if self.options.get("purge-client-integrity"):
            log.info("Removing cached client-integrity token...")
            self.cache.set(self._CACHE_KEY_CLIENT_INTEGRITY, None, 0)

        client_integrity = self.cache.get(self._CACHE_KEY_CLIENT_INTEGRITY)
        if client_integrity and isinstance(client_integrity, list) and len(client_integrity) == 2:
            log.info("Using cached client-integrity token")
            device_id, token = client_integrity
        else:
            log.info("Acquiring new client-integrity token...")
            device_id = random_token(32, CHOICES_ALPHA_NUM)
            client_integrity = TwitchClientIntegrity.acquire(
                self.session,
                channel,
                self.api.headers,
                device_id,
            )
            if not client_integrity:
                log.warning("No client-integrity token acquired")
                return None

            token, expiration = client_integrity
            self.cache.set(self._CACHE_KEY_CLIENT_INTEGRITY, [device_id, token], expires_at=fromtimestamp(expiration))

        return device_id, token

    def _access_token(self, is_live, channel_or_vod):
        response = ""
        data = (None, None)

        # try without a client-integrity token first (the web player did the same on 2023-05-31)
        if not self.options.get("force-client-integrity"):
            response, *data = self.api.access_token(is_live, channel_or_vod)

        # try again with a client-integrity token if the API response was erroneous
        if response != "token":
            client_integrity = self._client_integrity_token(channel_or_vod) if is_live else None
            response, *data = self.api.access_token(is_live, channel_or_vod, client_integrity)

            # unknown API response error: abort
            if response != "token":
                error, message = data
                raise PluginError(f"{error or 'Error'}: {message or 'Unknown error'}")

        # access token response was empty: stream is offline or channel doesn't exist
        if response == "token" and data[0] is None:
            raise NoStreamsError

        sig, token = data
        try:
            restricted_bitrates = self.api.parse_token(token)
        except PluginError:
            restricted_bitrates = []

        return sig, token, restricted_bitrates

    def _get_hls_streams_live(self):
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
        try:
            streams = TwitchHLSStream.parse_variant_playlist(
                self.session,
                url,
                start_offset=self.time_offset,
                # Check if the media playlists are accessible:
                # This is a workaround for checking the GQL API for the channel's live status,
                # which can be delayed by up to a minute.
                check_streams=True,
                disable_ads=self.get_option("disable-ads"),
                low_latency=self.get_option("low-latency"),
                **extra_params,
            )
        except OSError as err:
            # TODO: fix the "err" attribute set by HTTPSession.request()
            orig = getattr(err, "err", None)
            if isinstance(orig, HTTPError) and orig.response.status_code >= 400:
                # The playlist's error response may include JSON data with an error message
                with suppress(PluginError):
                    error = validate.Schema(
                        validate.parse_json(),
                        [
                            {
                                "type": "error",
                                "error": str,
                            },
                        ],
                        validate.get((0, "error")),
                    ).validate(orig.response.text)
                    # Only log error messages if the channel is actually live
                    if self.get_id():
                        log.error(error or "Could not access HLS playlist")
                # Don't raise and simply return no streams on 4xx/5xx playlist responses
                return
            raise PluginError(err) from err

        for name in restricted_bitrates:
            if name not in streams:
                log.warning(f"The quality '{name}' is not available since it requires a subscription.")

        return streams

    def _get_clips(self):
        try:
            sig, token, streams = self.api.clips(self.clip_id)
        except (PluginError, TypeError):
            return

        for quality, stream in streams:
            yield quality, HTTPStream(self.session, update_qsd(stream, {"sig": sig, "token": token}))

    def _get_streams(self):
        if self.video_id:
            return self._get_hls_streams_video()
        elif self.clip_id:
            return self._get_clips()
        elif self.channel:
            return self._get_hls_streams_live()


__plugin__ = Twitch
