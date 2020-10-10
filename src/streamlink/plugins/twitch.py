# -*- coding: utf-8 -*-
import argparse
import json
import logging
import re
import warnings
from collections import namedtuple
from random import random

import requests

from streamlink.compat import urlparse
from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json, parse_query
from streamlink.stream import HTTPStream, HLSStream
from streamlink.stream.hls import HLSStreamWorker
from streamlink.stream.hls_filtered import FilteredHLSStreamWriter, FilteredHLSStreamReader
from streamlink.stream.hls_playlist import M3U8, M3U8Parser, load as load_hls_playlist
from streamlink.utils.times import hours_minutes_seconds


log = logging.getLogger(__name__)

QUALITY_WEIGHTS = {
    "source": 1080,
    "1080": 1080,
    "high": 720,
    "720": 720,
    "medium": 480,
    "480": 480,
    "360": 360,
    "low": 240,
    "mobile": 120,
}

# Streamlink's client-id used for public API calls (don't steal this and register your own application on Twitch)
TWITCH_CLIENT_ID = "pwkzresl8kj2rdj6g7bvxl9ys1wly3j"
# Twitch's client-id used for private API calls (see issue #2680 for why we are doing this)
TWITCH_CLIENT_ID_PRIVATE = "kimne78kx3ncx6brgo4mv6wki5h1ko"

_url_re = re.compile(r"""
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

_access_token_schema = validate.Schema(
    {
        "token": validate.text,
        "sig": validate.text
    },
    validate.union((
        validate.get("sig"),
        validate.get("token")
    ))
)
_token_schema = validate.Schema(
    {
        "chansub": {
            "restricted_bitrates": validate.all(
                [validate.text],
                validate.filter(
                    lambda n: not re.match(r"(.+_)?archives|live|chunked", n)
                )
            )
        }
    },
    validate.get("chansub")
)
_stream_schema = validate.Schema(
    {
        "stream": validate.any(None, {
            "stream_type": validate.text,
            "broadcast_platform": validate.text,
            "channel": validate.any(None, {
                "broadcaster_software": validate.text
            })
        })
    },
    validate.get("stream")
)

Segment = namedtuple("Segment", "uri duration title key discontinuity ad byterange date map prefetch")

LOW_LATENCY_MAX_LIVE_EDGE = 2


class TwitchM3U8(M3U8):
    def __init__(self):
        super(TwitchM3U8, self).__init__()
        self.dateranges_ads = []


class TwitchM3U8Parser(M3U8Parser):
    def parse_tag_ext_x_twitch_prefetch(self, value):
        segments = self.m3u8.segments
        if segments:
            segments.append(segments[-1]._replace(uri=self.uri(value), prefetch=True))

    def parse_tag_ext_x_daterange(self, value):
        super(TwitchM3U8Parser, self).parse_tag_ext_x_daterange(value)
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
        super(TwitchHLSStreamWorker, self).__init__(reader, *args, **kwargs)

    def _reload_playlist(self, *args):
        return load_hls_playlist(*args, parser=TwitchM3U8Parser, m3u8=TwitchM3U8)

    def _playlist_reload_time(self, playlist, sequences):
        if self.stream.low_latency and sequences:
            return sequences[-1].segment.duration

        return super(TwitchHLSStreamWorker, self)._playlist_reload_time(playlist, sequences)

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

        return super(TwitchHLSStreamWorker, self).process_sequences(playlist, sequences)


class TwitchHLSStreamWriter(FilteredHLSStreamWriter):
    def should_filter_sequence(self, sequence):
        return self.stream.disable_ads and sequence.segment.ad


class TwitchHLSStreamReader(FilteredHLSStreamReader):
    __worker__ = TwitchHLSStreamWorker
    __writer__ = TwitchHLSStreamWriter


class TwitchHLSStream(HLSStream):
    def __init__(self, *args, **kwargs):
        super(TwitchHLSStream, self).__init__(*args, **kwargs)
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


class UsherService(object):
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
        # prepare_request is only available in requests 2.0+
        if hasattr(self.session.http, "prepare_request"):
            req = self.session.http.prepare_request(req)
        else:
            req = req.prepare()

        return req.url

    def channel(self, channel, **extra_params):
        return self._create_url("/api/channel/hls/{0}.m3u8".format(channel),
                                **extra_params)

    def video(self, video_id, **extra_params):
        return self._create_url("/vod/{0}".format(video_id), **extra_params)


class TwitchAPI(object):
    def __init__(self, session, beta=False, version=3):
        self.session = session
        self.subdomain = beta and "betaapi" or "api"
        self.version = version

    def call(self, path, format="json", schema=None, private=False, **extra_params):
        params = dict(as3="t", **extra_params)

        if len(format) > 0:
            url = "https://{0}.twitch.tv{1}.{2}".format(self.subdomain, path, format)
        else:
            url = "https://{0}.twitch.tv{1}".format(self.subdomain, path)

        headers = {'Accept': 'application/vnd.twitchtv.v{0}+json'.format(self.version),
                   'Client-ID': TWITCH_CLIENT_ID if not private else TWITCH_CLIENT_ID_PRIVATE}

        res = self.session.http.get(url, params=params, headers=headers)

        if format == "json":
            return self.session.http.json(res, schema=schema)
        else:
            return res

    def call_subdomain(self, subdomain, path, format="json", schema=None, **extra_params):
        subdomain_buffer = self.subdomain
        self.subdomain = subdomain
        try:
            return self.call(path, format=format, schema=schema, **extra_params)
        finally:
            self.subdomain = subdomain_buffer

    # Public API calls

    def users(self, **params):
        return self.call("/kraken/users", **params)

    def videos(self, video_id, **params):
        return self.call("/kraken/videos/{0}".format(video_id), **params)

    def channel_info(self, channel, **params):
        return self.call("/kraken/channels/{0}".format(channel), **params)

    def streams(self, channel_id, **params):
        return self.call("/kraken/streams/{0}".format(channel_id), **params)

    # Private API calls

    def access_token(self, endpoint, asset, **params):
        return self.call("/api/{0}/{1}/access_token".format(endpoint, asset), private=True, **params)

    def hosted_channel(self, **params):
        return self.call_subdomain("tmi", "/hosts", format="", **params)

    # Unsupported/Removed private API calls

    def channel_viewer_info(self, channel, **params):
        warnings.warn("The channel_viewer_info API call is unsupported and may stop working at any time")
        return self.call("/api/channels/{0}/viewer".format(channel), private=True, **params)

    def channel_subscription(self, channel, **params):
        warnings.warn("The channel_subscription API call has been removed and no longer works",
                      category=DeprecationWarning)
        return self.call("/api/channels/{0}/subscription".format(channel), private=True, **params)


class Twitch(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "oauth-token",
            sensitive=True,
            help=argparse.SUPPRESS
        ),
        PluginArgument(
            "cookie",
            sensitive=True,
            help=argparse.SUPPRESS
        ),
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

    _schema_metadata_empty = validate.transform(lambda _: (None,) * 3)
    _schema_metadata_channel = validate.Schema(
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
                validate.all(None, _schema_metadata_empty)
            )
        },
        validate.get("stream")
    )
    _schema_metadata_video = validate.Schema(validate.any(
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
        validate.all({}, _schema_metadata_empty)
    ))

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "twitch"

        return Plugin.stream_weight(key)

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_metadata(self):
        if self.video_id:
            (self.author, self.title, self.category) = self.api.videos(self.video_id, schema=self._schema_metadata_video)
        elif self.clip_name:
            self._get_clips()
        elif self._channel:
            (self.author, self.title, self.category) = self.api.streams(self.channel_id, schema=self._schema_metadata_channel)

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

    def __init__(self, url):
        Plugin.__init__(self, url)
        self._hosted_chain = []
        match = _url_re.match(url).groupdict()
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

        self.api = TwitchAPI(beta=self.subdomain == "beta",
                             session=self.session,
                             version=5)
        self.usher = UsherService(session=self.session)

    @property
    def channel(self):
        if not self._channel:
            if self.video_id:
                cdata = self._channel_from_video_id(self.video_id)
                self._channel = cdata["name"].lower()
                self._channel_id = cdata["_id"]
        return self._channel

    @channel.setter
    def channel(self, channel):
        self._channel = channel
        # channel id becomes unknown
        self._channel_id = None

    @property
    def channel_id(self):
        if not self._channel_id:
            # If the channel name is set, use that to look up the ID
            if self._channel:
                cdata = self._channel_from_login(self._channel)
                self._channel_id = cdata["_id"]

            # If the channel name is not set but the video ID is,
            # use that to look up both ID and name
            elif self.video_id:
                cdata = self._channel_from_video_id(self.video_id)
                self._channel = cdata["name"].lower()
                self._channel_id = cdata["_id"]
        return self._channel_id

    def _channel_from_video_id(self, video_id):
        vdata = self.api.videos(video_id)
        if "channel" not in vdata:
            raise PluginError("Unable to find video: {0}".format(video_id))
        return vdata["channel"]

    def _channel_from_login(self, channel):
        cdata = self.api.users(login=channel)
        if len(cdata["users"]):
            return cdata["users"][0]
        else:
            raise PluginError("Unable to find channel: {0}".format(channel))

    def _access_token(self, type="live"):
        try:
            if type == "live":
                endpoint = "channels"
                value = self.channel
            elif type == "video":
                endpoint = "vods"
                value = self.video_id

            sig, token = self.api.access_token(endpoint, value,
                                               schema=_access_token_schema)
        except PluginError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        return sig, token

    def _check_for_host(self):
        host_info = self.api.hosted_channel(include_logins=1, host=self.channel_id).json()["hosts"][0]
        if "target_login" in host_info and host_info["target_login"].lower() != self.channel.lower():
            log.info("{0} is hosting {1}".format(self.channel, host_info["target_login"]))
            return host_info["target_login"]

    def _check_for_rerun(self):
        stream = self.api.streams(self.channel_id, schema=_stream_schema)

        return stream and (
            stream["stream_type"] != "live"
            or stream["broadcast_platform"] == "rerun"
            or stream["channel"] and stream["channel"]["broadcaster_software"] == "watch_party_rerun"
        )

    def _get_hls_streams(self, stream_type="live"):
        log.debug("Getting {0} HLS streams for {1}".format(stream_type, self.channel))
        self._hosted_chain.append(self.channel)

        if stream_type == "live":
            if self.options.get("disable_reruns") and self._check_for_rerun():
                log.info("Reruns were disabled by command line option")
                return {}

            hosted_channel = self._check_for_host()
            if hosted_channel and self.options.get("disable_hosting"):
                log.info("hosting was disabled by command line option")
            elif hosted_channel:
                log.info("switching to {0}".format(hosted_channel))
                if hosted_channel in self._hosted_chain:
                    log.error(
                        u"A loop of hosted channels has been detected, "
                        "cannot find a playable stream. ({0})".format(
                            u" -> ".join(self._hosted_chain + [hosted_channel])))
                    return {}
                self.channel = hosted_channel
                return self._get_hls_streams(stream_type)

            # only get the token once the channel has been resolved
            sig, token = self._access_token(stream_type)
            url = self.usher.channel(self.channel, sig=sig, token=token, fast_bread=True)
        elif stream_type == "video":
            sig, token = self._access_token(stream_type)
            url = self.usher.video(self.video_id, nauthsig=sig, nauth=token)
        else:
            log.debug("Unknown HLS stream type: {0}".format(stream_type))
            return {}

        time_offset = self.params.get("t", 0)
        if time_offset:
            try:
                time_offset = hours_minutes_seconds(time_offset)
            except ValueError:
                time_offset = 0

        try:
            # If the stream is a VOD that is still being recorded the stream should start at the
            # beginning of the recording
            streams = TwitchHLSStream.parse_variant_playlist(
                self.session,
                url,
                start_offset=time_offset,
                force_restart=not stream_type == "live"
            )
        except IOError as err:
            err = str(err)
            if "404 Client Error" in err or "Failed to parse playlist" in err:
                return
            else:
                raise PluginError(err)

        try:
            token = parse_json(token, schema=_token_schema)
            for name in token["restricted_bitrates"]:
                if name not in streams:
                    log.warning("The quality '{0}' is not available since it requires a subscription.".format(name))
        except PluginError:
            pass

        return streams

    def _get_clips(self):
        data = json.dumps({'query': '''{{
            clip(slug: "{0}") {{
                broadcaster {{
                    displayName
                }}
                title
                videoQualities {{
                    quality
                    sourceURL
                }}
            }}
        }}'''.format(self.clip_name)})
        clip_data = self.session.http.post('https://gql.twitch.tv/gql',
                                           data=data,
                                           headers={'Client-ID': TWITCH_CLIENT_ID_PRIVATE},
                                           ).json()['data']['clip']
        log.trace('{0!r}'.format(clip_data))
        if not clip_data:
            return

        self.author = clip_data['broadcaster']['displayName']
        self.title = clip_data['title']

        streams = {}
        for quality_option in clip_data['videoQualities']:
            streams['{0}p'.format(quality_option['quality'])] = HTTPStream(self.session, quality_option['sourceURL'])
        return streams

    def _get_streams(self):
        if self.video_id:
            return self._get_hls_streams("video")
        elif self.clip_name:
            return self._get_clips()
        elif self._channel:
            return self._get_hls_streams("live")


__plugin__ = Twitch
