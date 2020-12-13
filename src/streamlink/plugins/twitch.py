import json
import logging
import re
from collections import namedtuple
from random import random
from urllib.parse import urlparse

import requests

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json, parse_query
from streamlink.stream import HLSStream, HTTPStream
from streamlink.stream.hls import HLSStreamReader, HLSStreamWorker, HLSStreamWriter
from streamlink.stream.hls_playlist import M3U8, M3U8Parser, load as load_hls_playlist
from streamlink.utils.times import hours_minutes_seconds

log = logging.getLogger(__name__)

Segment = namedtuple("Segment", "uri duration title key discontinuity ad byterange date map prefetch")

LOW_LATENCY_MAX_LIVE_EDGE = 2


class TwitchM3U8(M3U8):
    def __init__(self):
        super().__init__()
        self.dateranges_ads = []


class TwitchM3U8Parser(M3U8Parser):
    def parse_tag_ext_x_twitch_prefetch(self, value):
        segments = self.m3u8.segments
        if segments:
            segments.append(segments[-1]._replace(uri=self.uri(value), prefetch=True))

    def parse_tag_ext_x_daterange(self, value):
        super().parse_tag_ext_x_daterange(value)
        daterange = self.m3u8.dateranges[-1]
        is_ad = (
            daterange.classname == "twitch-stitched-ad"
            or str(daterange.id or "").startswith("stitched-ad-")
            or any(attr_key.startswith("X-TV-TWITCH-AD-") for attr_key in daterange.x.keys())
        )
        if is_ad:
            self.m3u8.dateranges_ads.append(daterange)

    def get_segment(self, uri):
        byterange = self.state.pop("byterange", None)
        extinf = self.state.pop("extinf", (0, None))
        date = self.state.pop("date", None)
        map_ = self.state.get("map")
        key = self.state.get("key")
        discontinuity = self.state.pop("discontinuity", False)
        ad = any(self.m3u8.is_date_in_daterange(date, daterange) for daterange in self.m3u8.dateranges_ads)

        return Segment(
            uri,
            extinf[0],
            extinf[1],
            key,
            discontinuity,
            ad,
            byterange,
            date,
            map_,
            prefetch=False
        )


class TwitchHLSStreamWorker(HLSStreamWorker):
    def __init__(self, reader, *args, **kwargs):
        self.had_content = False
        super().__init__(reader, *args, **kwargs)

    def _reload_playlist(self, *args):
        return load_hls_playlist(*args, parser=TwitchM3U8Parser, m3u8=TwitchM3U8)

    def _playlist_reload_time(self, playlist, sequences):
        if self.stream.low_latency and sequences:
            return sequences[-1].segment.duration

        return super()._playlist_reload_time(playlist, sequences)

    def process_sequences(self, playlist, sequences):
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

        return super().process_sequences(playlist, sequences)


class TwitchHLSStreamWriter(HLSStreamWriter):
    def should_filter_sequence(self, sequence):
        return self.stream.disable_ads and sequence.segment.ad


class TwitchHLSStreamReader(HLSStreamReader):
    __worker__ = TwitchHLSStreamWorker
    __writer__ = TwitchHLSStreamWriter


class TwitchHLSStream(HLSStream):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disable_ads = self.session.get_plugin_option("twitch", "disable-ads")
        self.low_latency = self.session.get_plugin_option("twitch", "low-latency")

    def open(self):
        if self.disable_ads:
            log.info("Will skip ad segments")
        if self.low_latency:
            live_edge = max(1, min(LOW_LATENCY_MAX_LIVE_EDGE, self.session.options.get("hls-live-edge")))
            self.session.options.set("hls-live-edge", live_edge)
            self.session.options.set("hls-segment-stream-data", True)
            log.info("Low latency streaming (HLS live edge: {0})".format(live_edge))

        reader = TwitchHLSStreamReader(self)
        reader.open()

        return reader

    @classmethod
    def _get_variant_playlist(cls, res):
        return load_hls_playlist(res.text, base_uri=res.url)


class UsherService:
    def __init__(self, session):
        self.session = session

    def _create_url(self, endpoint, **extra_params):
        url = "https://usher.ttvnw.net{0}".format(endpoint)
        params = {
            "player": "twitchweb",
            "p": int(random() * 999999),
            "type": "any",
            "allow_source": "true",
            "allow_audio_only": "true",
            "allow_spectre": "false",
        }
        params.update(extra_params)

        req = requests.Request("GET", url, params=params)
        req = self.session.http.prepare_request(req)

        return req.url

    def channel(self, channel, **extra_params):
        return self._create_url("/api/channel/hls/{0}.m3u8".format(channel),
                                **extra_params)

    def video(self, video_id, **extra_params):
        return self._create_url("/vod/{0}".format(video_id), **extra_params)


class TwitchAPI:
    # Streamlink's client-id used for public API calls (don't steal this and register your own application on Twitch)
    TWITCH_CLIENT_ID = "pwkzresl8kj2rdj6g7bvxl9ys1wly3j"
    # Twitch's client-id used for private API calls (see issue #2680 for why we are doing this)
    TWITCH_CLIENT_ID_PRIVATE = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    def __init__(self, session):
        self.session = session

    def _call(self, method="GET", subdomain="api", path="/", headers=None, private=False, data=None, **params):
        url = "https://{0}.twitch.tv{1}".format(subdomain, path)
        headers = headers or dict()
        headers.update({
            "Client-ID": self.TWITCH_CLIENT_ID if not private else self.TWITCH_CLIENT_ID_PRIVATE
        })

        return self.session.http.request(method, url, data=data, params=params, headers=headers)

    def call(self, path, schema=None, **params):
        headers = {"Accept": "application/vnd.twitchtv.v5+json"}
        res = self._call(path=path, headers=headers, **params)

        return self.session.http.json(res, schema=schema)

    def call_gql(self, data, schema=None, **params):
        res = self._call(method="POST", subdomain="gql", path="/gql", data=json.dumps(data), private=True, **params)

        return self.session.http.json(res, schema=schema)

    # Public API calls

    def channel_from_video_id(self, video_id):
        return self.call("/kraken/videos/{0}".format(video_id), schema=validate.Schema(
            {
                "channel": {
                    "_id": validate.any(int, validate.text),
                    "name": validate.text
                }
            },
            validate.get("channel"),
            validate.union((
                validate.all(validate.get("_id"), validate.transform(int)),
                validate.all(validate.get("name"), validate.transform(lambda n: n.lower()))
            ))
        ))

    def channel_from_login(self, channel):
        return self.call("/kraken/users", login=channel, schema=validate.Schema(
            {
                "users": [{
                    "_id": validate.any(int, validate.text)
                }]
            },
            validate.get("users"),
            validate.get(0),
            validate.get("_id"),
            validate.transform(int)
        ))

    def metadata_video(self, video_id):
        return self.call("/kraken/videos/{0}".format(video_id), schema=validate.Schema(validate.any(
            validate.all(
                {
                    "title": validate.text,
                    "game": validate.text,
                    "channel": validate.all(
                        {"display_name": validate.text},
                        validate.get("display_name")
                    )
                },
                validate.transform(lambda data: (data["channel"], data["title"], data["game"]))
            ),
            validate.all({}, validate.transform(lambda _: (None,) * 3))
        )))

    def metadata_channel(self, channel_id):
        return self.call("/kraken/streams/{0}".format(channel_id), schema=validate.Schema(
            {
                "stream": validate.any(
                    validate.all(
                        {"channel": {
                            "display_name": validate.text,
                            "game": validate.text,
                            "status": validate.text
                        }},
                        validate.get("channel"),
                        validate.transform(lambda ch: (ch["display_name"], ch["status"], ch["game"]))
                    ),
                    validate.all(None, validate.transform(lambda _: (None,) * 3))
                )
            },
            validate.get("stream")
        ))

    def hosted_channel(self, channel_id):
        return self.call("/hosts", subdomain="tmi", include_logins=1, host=channel_id, schema=validate.Schema(
            {
                "hosts": [{
                    "host_id": int,
                    "target_id": int,
                    "target_login": validate.text,
                    "target_display_name": validate.text
                }]
            },
            validate.get("hosts"),
            validate.get(0),
            validate.union((
                validate.get("host_id"),
                validate.get("target_id"),
                validate.get("target_login"),
                validate.get("target_display_name")
            ))
        ))

    # GraphQL API calls

    def access_token(self, is_live, channel_or_vod):
        request = {
            "operationName": "PlaybackAccessToken",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712"
                }
            },
            "variables": {
                "isLive": is_live,
                "login": channel_or_vod if is_live else "",
                "isVod": not is_live,
                "vodID": channel_or_vod if not is_live else "",
                "playerType": "embed"
            }
        }
        subschema = {
            "value": str,
            "signature": str,
            "__typename": "PlaybackAccessToken"
        }
        return self.call_gql(request, schema=validate.Schema(
            {"data": validate.any(
                validate.all(
                    {"streamPlaybackAccessToken": subschema},
                    validate.get("streamPlaybackAccessToken")
                ),
                validate.all(
                    {"videoPlaybackAccessToken": subschema},
                    validate.get("videoPlaybackAccessToken")
                )
            )},
            validate.get("data"),
            validate.union((
                validate.get("signature"),
                validate.get("value")
            ))
        ))

    def parse_token(self, tokenstr):
        return parse_json(tokenstr, schema=validate.Schema(
            {
                "chansub": {
                    "restricted_bitrates": validate.all(
                        [str],
                        validate.filter(
                            lambda n: not re.match(r"(.+_)?archives|live|chunked", n)
                        )
                    )
                }
            },
            validate.get("chansub"),
            validate.get("restricted_bitrates")
        ))

    def clips(self, clipname):
        query = """{{
            clip(slug: "{clipname}") {{
                broadcaster {{
                    displayName
                }}
                title
                game {{
                    name
                }}
                videoQualities {{
                    quality
                    sourceURL
                }}
            }}
        }}""".format(clipname=clipname)

        return self.call_gql({"query": query}, schema=validate.Schema(
            {"data": {
                "clip": validate.any(None, validate.all({
                    "broadcaster": validate.all({"displayName": validate.text}, validate.get("displayName")),
                    "title": validate.text,
                    "game": validate.all({"name": validate.text}, validate.get("name")),
                    "videoQualities": [validate.all({
                        "quality": validate.all(
                            validate.text,
                            validate.transform(lambda q: "{0}p".format(q))
                        ),
                        "sourceURL": validate.url()
                    }, validate.union((
                        validate.get("quality"),
                        validate.get("sourceURL")
                    )))]
                }, validate.union((
                    validate.get("broadcaster"),
                    validate.get("title"),
                    validate.get("game"),
                    validate.get("videoQualities")
                ))))
            }},
            validate.get("data"),
            validate.get("clip")
        ))

    def stream_metadata(self, channel):
        request = {
            "operationName": "StreamMetadata",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "1c719a40e481453e5c48d9bb585d971b8b372f8ebb105b17076722264dfa5b3e"
                }
            },
            "variables": {
                "channelLogin": channel
            }
        }

        return self.call_gql(request, schema=validate.Schema(
            {
                "data": {
                    "user": {
                        "stream": {
                            "type": str,
                        }
                    }
                }
            },
            validate.get("data"),
            validate.get("user"),
            validate.get("stream")
        ))


class Twitch(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "disable-hosting",
            action="store_true",
            help="""
            Do not open the stream if the target channel is hosting another channel.
            """
        ),
        PluginArgument(
            "disable-ads",
            action="store_true",
            help="""
            Skip embedded advertisement segments at the beginning or during a stream.
            Will cause these segments to be missing from the stream.
            """
        ),
        PluginArgument(
            "disable-reruns",
            action="store_true",
            help="""
            Do not open the stream if the target channel is currently broadcasting a rerun.
            """
        ),
        PluginArgument(
            "low-latency",
            action="store_true",
            help="""
            Enables low latency streaming by prefetching HLS segments.
            Sets --hls-segment-stream-data to true and --hls-live-edge to {live_edge}, if it is higher.
            Reducing --hls-live-edge to 1 will result in the lowest latency possible.

            Low latency streams have to be enabled by the broadcasters on Twitch themselves.
            Regular streams can cause buffering issues with this option enabled.

            Note: The caching/buffering settings of the chosen player may need to be adjusted as well.
            Please refer to the player's own documentation for the required parameters and its configuration.
            Player parameters can be set via Streamlink's --player or --player-args parameters.
            """.format(live_edge=LOW_LATENCY_MAX_LIVE_EDGE)
        )
    )

    _re_url = re.compile(r"""
        https?://(?:(?P<subdomain>[\w\-]+)\.)?twitch\.tv/
        (?:
            videos/(?P<videos_id>\d+)
            |
            (?P<channel>[^/]+)
            (?:
                /video/(?P<video_id>\d+)
                |
                /clip/(?P<clip_name>[\w]+)
            )?
        )
    """, re.VERBOSE)

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url)

    def __init__(self, url):
        super().__init__(url)
        match = self._re_url.match(url).groupdict()
        parsed = urlparse(url)
        self.params = parse_query(parsed.query)
        self.subdomain = match.get("subdomain")
        self.video_id = None
        self._channel_id = None
        self._channel = None
        self.clip_name = None
        self.title = None
        self.author = None
        self.category = None

        if self.subdomain == "player":
            # pop-out player
            if self.params.get("video"):
                self.video_id = self.params["video"]
            self._channel = self.params.get("channel")
        elif self.subdomain == "clips":
            # clip share URL
            self.clip_name = match.get("channel")
        else:
            self._channel = match.get("channel") and match.get("channel").lower()
            self.video_id = match.get("video_id") or match.get("videos_id")
            self.clip_name = match.get("clip_name")

        self.api = TwitchAPI(session=self.session)
        self.usher = UsherService(session=self.session)

    def get_title(self):
        if self.title is None:
            self._get_metadata()
        return self.title

    def get_author(self):
        if self.author is None:
            self._get_metadata()
        return self.author

    def get_category(self):
        if self.category is None:
            self._get_metadata()
        return self.category

    def _get_metadata(self):
        if self.video_id:
            (self.author, self.title, self.category) = self.api.metadata_video(self.video_id)
        elif self.clip_name:
            self._get_clips()
        elif self._channel:
            (self.author, self.title, self.category) = self.api.metadata_channel(self.channel_id)

    @property
    def channel(self):
        if not self._channel:
            if self.video_id:
                self._channel_from_video_id(self.video_id)
        return self._channel

    @property
    def channel_id(self):
        if not self._channel_id:
            if self._channel:
                self._channel_from_login(self._channel)
            elif self.video_id:
                self._channel_from_video_id(self.video_id)
        return self._channel_id

    def _channel_from_video_id(self, video_id):
        try:
            self._channel_id, self._channel = self.api.channel_from_video_id(video_id)
        except PluginError:
            raise PluginError("Unable to find video: {0}".format(video_id))

    def _channel_from_login(self, channel):
        try:
            self._channel_id = self.api.channel_from_login(channel)
        except PluginError:
            raise PluginError("Unable to find channel: {0}".format(channel))

    def _access_token(self, is_live, channel_or_vod):
        try:
            sig, token = self.api.access_token(is_live, channel_or_vod)
        except PluginError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        try:
            restricted_bitrates = self.api.parse_token(token)
        except PluginError:
            restricted_bitrates = []

        return sig, token, restricted_bitrates

    def _switch_to_hosted_channel(self):
        disabled = self.options.get("disable_hosting")
        hosted_chain = [self.channel]
        while True:
            try:
                host_id, target_id, login, display_name = self.api.hosted_channel(self.channel_id)
            except PluginError:
                return False

            log.info("{0} is hosting {1}".format(self.channel, login))
            if disabled:
                log.info("hosting was disabled by command line option")
                return True

            if login in hosted_chain:
                loop = " -> ".join(hosted_chain + [login])
                log.error("A loop of hosted channels has been detected, cannot find a playable stream. ({0})".format(loop))
                return True

            hosted_chain.append(login)
            log.info("switching to {0}".format(login))
            self._channel_id = target_id
            self._channel = login
            self.author = display_name

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
        if self._switch_to_hosted_channel():
            return
        if self._check_for_rerun():
            return

        # only get the token once the channel has been resolved
        log.debug("Getting live HLS streams for {0}".format(self.channel))
        self.session.http.headers.update({
            "referer": "https://player.twitch.tv",
            "origin": "https://player.twitch.tv",
        })
        sig, token, restricted_bitrates = self._access_token(True, self.channel)
        url = self.usher.channel(self.channel, sig=sig, token=token, fast_bread=True)

        return self._get_hls_streams(url, restricted_bitrates)

    def _get_hls_streams_video(self):
        log.debug("Getting video HLS streams for {0}".format(self.channel))
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
                log.warning("The quality '{0}' is not available since it requires a subscription.".format(name))

        return streams

    def _get_clips(self):
        try:
            (self.author, self.title, self.category, streams) = self.api.clips(self.clip_name)
        except (PluginError, TypeError):
            return

        for quality, stream in streams:
            yield quality, HTTPStream(self.session, stream)

    def _get_streams(self):
        if self.video_id:
            return self._get_hls_streams_video()
        elif self.clip_name:
            return self._get_clips()
        elif self._channel:
            return self._get_hls_streams_live()


__plugin__ = Twitch
