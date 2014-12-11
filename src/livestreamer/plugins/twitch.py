import re

import requests

from random import random

from livestreamer.compat import urlparse
from livestreamer.exceptions import NoStreamsError, PluginError, StreamError
from livestreamer.plugin import Plugin, PluginOptions
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_json, parse_query
from livestreamer.stream import (
    HTTPStream, HLSStream, FLVPlaylist, extract_flv_header_tags
)

try:
    from itertools import izip as zip
except ImportError:
    pass

QUALITY_WEIGHTS = {
    "source": 1080,
    "high": 720,
    "medium": 480,
    "low": 240,
    "mobile": 120,
}


_url_re = re.compile(r"""
    http(s)?://
    (?:
        (?P<subdomain>\w+)
        \.
    )?
    twitch.tv
    /
    (?P<channel>[^/]+)
    (?:
        /
        (?P<video_type>[bcv])
        /
        (?P<video_id>\d+)
    )?
""", re.VERBOSE)
_time_re = re.compile("""
    (?:
        (?P<hours>\d+)h
    )?
    (?:
        (?P<minutes>\d+)m
    )?
    (?:
        (?P<seconds>\d+)s
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


def time_to_offset(t):
    match = _time_re.match(t)
    if match:
        offset = int(match.group("hours") or "0") * 60 * 60
        offset += int(match.group("minutes") or "0") * 60
        offset += int(match.group("seconds") or "0")
    else:
        offset = 0

    return offset


class UsherService(object):
    def _create_url(self, endpoint, **extra_params):
        url = "http://usher.twitch.tv{0}".format(endpoint)
        params = {
            "player": "twitchweb",
            "p": int(random() * 999999),
            "type": "any",
            "allow_source": "true",
            "allow_audio_only": "true",
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
    def __init__(self, beta=False):
        self.oauth_token = None
        self.subdomain = beta and "betaapi" or "api"

    def add_cookies(self, cookies):
        http.parse_cookies(cookies, domain="twitch.tv")

    def call(self, path, format="json", schema=None, **extra_params):
        params = dict(as3="t", **extra_params)

        if self.oauth_token:
            params["oauth_token"] = self.oauth_token

        url = "https://{0}.twitch.tv{1}.{2}".format(self.subdomain, path, format)

        # The certificate used by Twitch cannot be verified on some OpenSSL versions.
        res = http.get(url, params=params, verify=False)

        if format == "json":
            return http.json(res, schema=schema)
        else:
            return res

    def access_token(self, endpoint, asset, **params):
        return self.call("/api/{0}/{1}/access_token".format(endpoint, asset), **params)

    def channel_info(self, channel, **params):
        return self.call("/api/channels/{0}".format(channel), **params)

    def channel_subscription(self, channel, **params):
        return self.call("/api/channels/{0}/subscription".format(channel), **params)

    def channel_viewer_info(self, channel, **params):
        return self.call("/api/channels/{0}/viewer".format(channel), **params)

    def token(self, **params):
        return self.call("/api/viewer/token", **params)

    def user(self, **params):
        return self.call("/kraken/user", **params)

    def videos(self, video_id, **params):
        return self.call("/api/videos/{0}".format(video_id), **params)

    def viewer_info(self, **params):
        return self.call("/api/viewer/info", **params)


class Twitch(Plugin):
    options = PluginOptions({
        "cookie": None,
        "oauth_token": None,
    })

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

        match = _url_re.match(url).groupdict()
        self.channel = match.get("channel").lower()
        self.subdomain = match.get("subdomain")
        self.video_type = match.get("video_type")
        self.video_id = match.get("video_id")

        parsed = urlparse(url)
        self.params = parse_query(parsed.query)

        self.api = TwitchAPI(beta=self.subdomain == "beta")
        self.usher = UsherService()

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

            if start_offset >= chunk_start and start_offset <= chunk_stop:
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
            elif chunk_start >= start_offset and chunk_start < stop_offset:
                playlist_streams.append(chunk_stream)

            playlist_offset += chunk_length

        return FLVPlaylist(self.session, playlist_streams,
                           tags=playlist_tags, duration=playlist_duration)

    def _get_video_streams(self):
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
            videos["start_offset"] += time_to_offset(self.params.get("t"))

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

    def _get_hls_streams(self, type="live"):
        self._authenticate()
        sig, token = self._access_token(type)
        if type == "live":
            url = self.usher.channel(self.channel, sig=sig, token=token)
        elif type == "video":
            url = self.usher.video(self.video_id, nauthsig=sig, nauth=token)

        try:
            streams = HLSStream.parse_variant_playlist(self.session, url)
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

    def _get_streams(self):
        if self.video_id:
            if self.video_type == "v":
                return self._get_hls_streams("video")
            else:
                return self._get_video_streams()
        else:
            return self._get_hls_streams("live")


__plugin__ = Twitch
