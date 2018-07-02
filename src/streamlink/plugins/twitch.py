# coding=utf-8
import re
import warnings
from random import random

import requests

from streamlink.compat import urlparse
from streamlink.exceptions import NoStreamsError, PluginError, StreamError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_json, parse_query
from streamlink.stream import (
    HTTPStream, HLSStream, FLVPlaylist, extract_flv_header_tags
)
from streamlink.utils.times import hours_minutes_seconds

try:
    from itertools import izip as zip
except ImportError:
    pass

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

TWITCH_CLIENT_ID = "pwkzresl8kj2rdj6g7bvxl9ys1wly3j"

_url_re = re.compile(r"""
    http(s)?://
    (?:
        (?P<subdomain>[\w\-]+)
        \.
    )?
    twitch.tv/
    (?:
        videos/(?P<videos_id>\d+)|
        (?P<channel>[^/]+)
    )
    (?:
        /
        (?P<video_type>[bcv])
        /
        (?P<video_id>\d+)
    )?
    (?:
        /
        (?P<clip_name>[\w]+)
    )?
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
_user_schema = validate.Schema(
    {
        validate.optional("display_name"): validate.text
    },
    validate.get("display_name")
)
_video_schema = validate.Schema(
    {
        "chunks": {
            validate.text: [{
                "length": int,
                "url": validate.any(None, validate.url(scheme="http")),
                "upkeep": validate.any("pass", "fail", None)
            }]
        },
        "restrictions": {validate.text: validate.text},
        "start_offset": int,
        "end_offset": int,
    }
)
_viewer_info_schema = validate.Schema(
    {
        validate.optional("login"): validate.text
    },
    validate.get("login")
)
_viewer_token_schema = validate.Schema(
    {
        validate.optional("token"): validate.text
    },
    validate.get("token")
)
_quality_options_schema = validate.Schema(
    {
        "quality_options": validate.all(
            [{
                "quality": validate.any(validate.text, None),
                "source": validate.url(
                    scheme="https",
                    path=validate.endswith(".mp4")
                )
            }]
        )
    },
    validate.get("quality_options")
)


class UsherService(object):
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
        if hasattr(http, "prepare_request"):
            req = http.prepare_request(req)
        else:
            req = req.prepare()

        return req.url

    def channel(self, channel, **extra_params):
        return self._create_url("/api/channel/hls/{0}.m3u8".format(channel),
                                **extra_params)

    def video(self, video_id, **extra_params):
        return self._create_url("/vod/{0}".format(video_id), **extra_params)


class TwitchAPI(object):
    def __init__(self, beta=False, version=3):
        self.oauth_token = None
        self.subdomain = beta and "betaapi" or "api"
        self.version = version

    def add_cookies(self, cookies):
        http.parse_cookies(cookies, domain="twitch.tv")

    def call(self, path, format="json", schema=None, **extra_params):
        params = dict(as3="t", **extra_params)

        if self.oauth_token:
            params["oauth_token"] = self.oauth_token

        if len(format) > 0:
            url = "https://{0}.twitch.tv{1}.{2}".format(self.subdomain, path, format)
        else:
            url = "https://{0}.twitch.tv{1}".format(self.subdomain, path)

        headers = {'Accept': 'application/vnd.twitchtv.v{0}+json'.format(self.version),
                   'Client-ID': TWITCH_CLIENT_ID}

        res = http.get(url, params=params, headers=headers)

        if format == "json":
            return http.json(res, schema=schema)
        else:
            return res

    def call_subdomain(self, subdomain, path, format="json", schema=None, **extra_params):
        subdomain_buffer = self.subdomain
        self.subdomain = subdomain
        response = self.call(path, format=format, schema=schema, **extra_params)
        self.subdomain = subdomain_buffer
        return response

    # Public API calls

    def user(self, **params):
        return self.call("/kraken/user", **params)

    def users(self, **params):
        return self.call("/kraken/users", **params)

    def videos(self, video_id, **params):
        return self.call("/kraken/videos/{0}".format(video_id), **params)

    def channel_info(self, channel, **params):
        return self.call("/kraken/channels/{0}".format(channel), **params)

    # Private API calls

    def access_token(self, endpoint, asset, **params):
        return self.call("/api/{0}/{1}/access_token".format(endpoint, asset), **params)

    def token(self, **params):
        return self.call("/api/viewer/token", **params)

    def viewer_info(self, **params):
        return self.call("/api/viewer/info", **params)

    def hosted_channel(self, **params):
        return self.call_subdomain("tmi", "/hosts", format="", **params)

    def clip_status(self, channel, clip_name, schema):
        return http.json(self.call_subdomain("clips", "/api/v2/clips/" + clip_name + "/status", format=""),
                         schema=schema)

    # Unsupported/Removed private API calls

    def channel_viewer_info(self, channel, **params):
        warnings.warn("The channel_viewer_info API call is unsupported and may stop working at any time")
        return self.call("/api/channels/{0}/viewer".format(channel), **params)

    def channel_subscription(self, channel, **params):
        warnings.warn("The channel_subscription API call has been removed and no longer works",
                      category=DeprecationWarning)
        return self.call("/api/channels/{0}/subscription".format(channel), **params)


class Twitch(Plugin):
    arguments = PluginArguments(
        PluginArgument("oauth-token",
                       sensitive=True,
                       metavar="TOKEN",
                       help="""
        An OAuth token to use for Twitch authentication.
        Use --twitch-oauth-authenticate to create a token.
        """),
        PluginArgument("cookie",
                       sensitive=True,
                       metavar="COOKIES",
                       help="""
        Twitch cookies to authenticate to allow access to subscription channels.

        Example:

          "_twitch_session_id=xxxxxx; persistent=xxxxx"

        Note: This method is the old and clunky way of authenticating with
        Twitch, using --twitch-oauth-authenticate is the recommended and
        simpler way of doing it now.
        """
                       ),
        PluginArgument("disable-hosting",
                       action="store_true",
                       help="""
        Do not open the stream if the target channel is hosting another channel.
        """
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

    def __init__(self, url):
        Plugin.__init__(self, url)
        self._hosted_chain = []
        match = _url_re.match(url).groupdict()
        parsed = urlparse(url)
        self.params = parse_query(parsed.query)
        self.subdomain = match.get("subdomain")
        self.video_id = None
        self.video_type = None
        self._channel_id = None
        self._channel = None
        self.clip_name = None

        if self.subdomain == "player":
            # pop-out player
            if self.params.get("video"):
                try:
                    self.video_type = self.params["video"][0]
                    self.video_id = self.params["video"][1:]
                except IndexError:
                    self.logger.debug("Invalid video param: {0}", self.params["video"])
            self._channel = self.params.get("channel")
        elif self.subdomain == "clips":
            # clip share URL
            self.clip_name = match.get("channel")
        else:
            self._channel = match.get("channel") and match.get("channel").lower()
            self.video_type = match.get("video_type")
            if match.get("videos_id"):
                self.video_type = "v"
            self.video_id = match.get("video_id") or match.get("videos_id")
            self.clip_name = match.get("clip_name")

        self.api = TwitchAPI(beta=self.subdomain == "beta", version=5)
        self.usher = UsherService()

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

    def _authenticate(self):
        if self.api.oauth_token:
            return

        oauth_token = self.options.get("oauth_token")
        cookies = self.options.get("cookie")

        if oauth_token:
            self.logger.info("Attempting to authenticate using OAuth token")
            self.api.oauth_token = oauth_token
            user = self.api.user(schema=_user_schema)

            if user:
                self.logger.info("Successfully logged in as {0}", user)
            else:
                self.logger.error("Failed to authenticate, the access token "
                                  "is invalid or missing required scope")
        elif cookies:
            self.logger.info("Attempting to authenticate using cookies")

            self.api.add_cookies(cookies)
            self.api.oauth_token = self.api.token(schema=_viewer_token_schema)
            login = self.api.viewer_info(schema=_viewer_info_schema)

            if login:
                self.logger.info("Successfully logged in as {0}", login)
            else:
                self.logger.error("Failed to authenticate, your cookies "
                                  "may have expired")

    def _create_playlist_streams(self, videos):
        start_offset = int(videos.get("start_offset", 0))
        stop_offset = int(videos.get("end_offset", 0))
        streams = {}

        for quality, chunks in videos.get("chunks").items():
            if not chunks:
                if videos.get("restrictions", {}).get(quality) == "chansub":
                    self.logger.warning("The quality '{0}' is not available "
                                        "since it requires a subscription.",
                                        quality)
                continue

            # Rename 'live' to 'source'
            if quality == "live":
                quality = "source"

            chunks_filtered = list(filter(lambda c: c["url"], chunks))
            if len(chunks) != len(chunks_filtered):
                self.logger.warning("The video '{0}' contains invalid chunks. "
                                    "There will be missing data.", quality)
                chunks = chunks_filtered

            chunks_duration = sum(c.get("length") for c in chunks)

            # If it's a full broadcast we just use all the chunks
            if start_offset == 0 and chunks_duration == stop_offset:
                # No need to use the FLV concat if it's just one chunk
                if len(chunks) == 1:
                    url = chunks[0].get("url")
                    stream = HTTPStream(self.session, url)
                else:
                    chunks = [HTTPStream(self.session, c.get("url")) for c in chunks]
                    stream = FLVPlaylist(self.session, chunks,
                                         duration=chunks_duration)
            else:
                try:
                    stream = self._create_video_clip(chunks,
                                                     start_offset,
                                                     stop_offset)
                except StreamError as err:
                    self.logger.error("Error while creating video '{0}': {1}",
                                      quality, err)
                    continue

            streams[quality] = stream

        return streams

    def _create_video_clip(self, chunks, start_offset, stop_offset):
        playlist_duration = stop_offset - start_offset
        playlist_offset = 0
        playlist_streams = []
        playlist_tags = []

        for chunk in chunks:
            chunk_url = chunk["url"]
            chunk_length = chunk["length"]
            chunk_start = playlist_offset
            chunk_stop = chunk_start + chunk_length
            chunk_stream = HTTPStream(self.session, chunk_url)

            if chunk_start <= start_offset <= chunk_stop:
                try:
                    headers = extract_flv_header_tags(chunk_stream)
                except IOError as err:
                    raise StreamError("Error while parsing FLV: {0}", err)

                if not headers.metadata:
                    raise StreamError("Missing metadata tag in the first chunk")

                metadata = headers.metadata.data.value
                keyframes = metadata.get("keyframes")

                if not keyframes:
                    if chunk["upkeep"] == "fail":
                        raise StreamError("Unable to seek into muted chunk, try another timestamp")
                    else:
                        raise StreamError("Missing keyframes info in the first chunk")

                keyframe_offset = None
                keyframe_offsets = keyframes.get("filepositions")
                keyframe_times = [playlist_offset + t for t in keyframes.get("times")]
                for time, offset in zip(keyframe_times, keyframe_offsets):
                    if time > start_offset:
                        break

                    keyframe_offset = offset

                if keyframe_offset is None:
                    raise StreamError("Unable to find a keyframe to seek to "
                                      "in the first chunk")

                chunk_headers = dict(Range="bytes={0}-".format(int(keyframe_offset)))
                chunk_stream = HTTPStream(self.session, chunk_url,
                                          headers=chunk_headers)
                playlist_streams.append(chunk_stream)
                for tag in headers:
                    playlist_tags.append(tag)
            elif start_offset <= chunk_start < stop_offset:
                playlist_streams.append(chunk_stream)

            playlist_offset += chunk_length

        return FLVPlaylist(self.session, playlist_streams,
                           tags=playlist_tags, duration=playlist_duration)

    def _get_video_streams(self):
        self.logger.debug("Getting video steams for {0} (type={1})".format(self.video_id, self.video_type))
        self._authenticate()

        if self.video_type == "b":
            self.video_type = "a"

        try:
            videos = self.api.videos(self.video_type + self.video_id,
                                     schema=_video_schema)
        except PluginError as err:
            if "HTTP/1.1 0 ERROR" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        # Parse the "t" query parameter on broadcasts and adjust
        # start offset if needed.
        time_offset = self.params.get("t")
        if time_offset:
            try:
                time_offset = hours_minutes_seconds(time_offset)
            except ValueError:
                time_offset = 0

            videos["start_offset"] += time_offset

        return self._create_playlist_streams(videos)

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
            self.logger.info("{0} is hosting {1}".format(self.channel, host_info["target_login"]))
            return host_info["target_login"]

    def _get_hls_streams(self, stream_type="live"):
        self.logger.debug("Getting {0} HLS streams for {1}".format(stream_type, self.channel))
        self._authenticate()
        self._hosted_chain.append(self.channel)

        if stream_type == "live":
            hosted_channel = self._check_for_host()
            if hosted_channel and self.options.get("disable_hosting"):
                self.logger.info("hosting was disabled by command line option")
            elif hosted_channel:
                self.logger.info("switching to {0}", hosted_channel)
                if hosted_channel in self._hosted_chain:
                    self.logger.error(u"A loop of hosted channels has been detected, "
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
            self.logger.debug("Unknown HLS stream type: {0}".format(stream_type))
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
            streams = HLSStream.parse_variant_playlist(self.session, url,
                                                       start_offset=time_offset,
                                                       force_restart=not stream_type == "live")
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
                    self.logger.warning("The quality '{0}' is not available "
                                        "since it requires a subscription.",
                                        name)
        except PluginError:
            pass

        return streams

    def _get_clips(self):
        quality_options = self.api.clip_status(self.channel, self.clip_name, schema=_quality_options_schema)
        streams = {}
        for quality_option in quality_options:
            streams[quality_option["quality"]] = HTTPStream(self.session, quality_option["source"])
        return streams

    def _get_streams(self):
        if self.video_id:
            if self.video_type == "v":
                return self._get_hls_streams("video")
            else:
                return self._get_video_streams()
        elif self.clip_name:
            return self._get_clips()
        elif self._channel:
            return self._get_hls_streams("live")


__plugin__ = Twitch
