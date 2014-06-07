import re
import requests

from itertools import starmap
from random import random

try:
    from itertools import izip
except ImportError:
    izip = zip

from livestreamer.compat import urlparse, urljoin
from livestreamer.exceptions import NoStreamsError, PluginError, StreamError
from livestreamer.options import Options
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import (HTTPStream, HLSStream, FLVPlaylist,
                                 extract_flv_header_tags)
from livestreamer.utils import parse_json, parse_qsd

__all__ = ["PluginBase", "APIBase"]

QUALITY_WEIGHTS = {
    "source": 1080,
    "high": 720,
    "medium": 480,
    "low": 240,
    "mobile": 120,
}
USHER_SELECT_PATH = "/select/{0}.json"

_url_re = re.compile(r"""
    http(s)?://
    (?:
        (?P<subdomain>\w+)
        \.
    )?
    (?P<domain>twitch.tv|justin.tv)
    /
    (?P<channel>[^/]+)
    (?:
        /
        (?P<video_type>[bc])
        /
        (?P<video_id>\d+)
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


class UsherService(object):
    def __init__(self, host="justin.tv"):
        self.host = host

    def url(self, path, *args, **kwargs):
        path = path.format(*args, **kwargs)
        return urljoin("http://usher." + self.host, path)

    def select(self, channel, password=None, **extra_params):
        url = self.url(USHER_SELECT_PATH, channel)
        params = dict(p=int(random() * 999999), type="any",
                      allow_source="true", allow_audio_only="true",
                      private_code=password or "null", **extra_params)

        req = requests.Request("GET", url, params=params)
        # prepare_request is only available in requests 2.0+
        if hasattr(http, "prepare_request"):
            req = http.prepare_request(req)
        else:
            req = req.prepare()

        return req.url


class APIBase(object):
    def __init__(self, host="justin.tv", beta=False):
        self.beta = beta
        self.host = host
        self.oauth_token = None
        self.subdomain = beta and "betaapi" or "api"

    def add_cookies(self, cookies):
        http.parse_cookies(cookies, domain=self.host)

    def call(self, path, format="json", host=None, schema=None, **extra_params):
        params = dict(as3="t", **extra_params)

        if self.oauth_token:
            params["oauth_token"] = self.oauth_token

        url = "https://{0}.{1}{2}.{3}".format(self.subdomain, host or self.host,
                                              path, format)
        # The certificate used by Twitch cannot be verified in some environments.
        res = http.get(url, params=params, verify=False)

        if format == "json":
            return http.json(res, schema=schema)
        elif format == "xml":
            return http.xml(res, schema=schema)
        else:
            return res

    def channel_access_token(self, channel, **params):
        return self.call("/api/channels/{0}/access_token".format(channel),
                         host="twitch.tv", **params)

    def token(self, **params):
        return self.call("/api/viewer/token", host="twitch.tv", **params)

    def viewer_info(self, **params):
        return self.call("/api/viewer/info", host="twitch.tv", **params)


class PluginBase(Plugin):
    options = Options({
        "cookie": None,
        "password": None,
    })

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "justintv"

        return Plugin.stream_weight(key)

    def __init__(self, url):
        Plugin.__init__(self, url)

        try:
            match = _url_re.match(url).groupdict()
            self.channel = match.get("channel").lower()
            self.subdomain = match.get("subdomain")
            self.video_type = match.get("video_type")
            self.video_id = match.get("video_id")
            self.usher = UsherService(match.get("domain"))

            parsed = urlparse(url)
            self.params = parse_qsd(parsed.query)
        except AttributeError:
            self.channel = None
            self.params = None
            self.subdomain = None
            self.video_id = None
            self.video_type = None
            self.usher = None

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
                    self.logger.error("Error while creating video clip '{0}': {1}",
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
            chunk_url = chunk.get("url")
            chunk_length = chunk.get("length")
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
                    raise StreamError("Missing keyframes info in the first chunk")

                keyframe_offset = None
                keyframe_offsets = keyframes.get("filepositions")
                keyframe_times = [playlist_offset + t for t in keyframes.get("times")]
                for time, offset in izip(keyframe_times, keyframe_offsets):
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

    def _get_streams(self):
        if not self.channel:
            return

        if self.video_id:
            return self._get_video_streams()
        else:
            return self._get_live_streams()

    def _authenticate(self):
        cookies = self.options.get("cookie")

        if cookies and not self.api.oauth_token:
            self.logger.info("Attempting to authenticate using cookies")

            self.api.add_cookies(cookies)
            self.api.oauth_token = self.api.token(schema=_viewer_token_schema)
            login = self.api.viewer_info(schema=_viewer_info_schema)

            if login:
                self.logger.info("Successfully logged in as {0}", login)
            else:
                self.logger.error("Failed to authenticate, your cookies "
                                  "may have expired")

    def _access_token(self):
        try:
            sig, token = self.api.channel_access_token(
                self.channel, schema=_access_token_schema
            )
        except PluginError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        return sig, token

    def _get_live_streams(self):
        self._authenticate()
        sig, token = self._access_token()
        url = self.usher.select(self.channel,
                                password=self.options.get("password"),
                                nauthsig=sig,
                                nauth=token)

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

        return dict(starmap(self._check_stream_name, streams.items()))

    def _get_video_streams(self):
        pass

    def _check_stream_name(self, name, stream):
        if name.startswith("iphone"):
            name = name.replace("iphone", "")

        return name, stream

