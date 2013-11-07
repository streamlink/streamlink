import hmac
import re

from collections import defaultdict
from hashlib import sha1
from random import random

try:
    from itertools import izip
except ImportError:
    izip = zip

from livestreamer.compat import bytes, quote, urljoin
from livestreamer.exceptions import NoStreamsError, PluginError, StreamError
from livestreamer.options import Options
from livestreamer.plugin import Plugin
from livestreamer.stream import (HTTPStream, RTMPStream, HLSStream,
                                 FLVPlaylist, extract_flv_header_tags)
from livestreamer.utils import (urlget, urlresolve,
                                swfverify, res_json, verifyjson)


__all__ = ["JustinTVBase"]

HLS_TOKEN_KEY = b"Wd75Yj9sS26Lmhve"
HLS_TOKEN_PATH = "/stream/iphone_token/{0}.json"
HLS_PLAYLIST_PATH = "/stream/multi_playlist/{0}.m3u8?token={1}&hd=true&allow_cdn=true"
USHER_FIND_PATH = "/find/{0}.json"
REQUIRED_RTMP_KEYS = ("connect", "play", "type", "token")
QUALITY_WEIGHTS = {
    "mobile_source": 480,
    "mobile_high": 330,
    "mobile_medium": 260,
    "mobile_low": 170,
    "mobile_mobile": 120
}
URL_PATTERN = (r"http(s)?://([\w\.]+)?(?P<domain>twitch.tv|justin.tv)/(?P<channel>\w+)"
               r"(/(?P<video_type>[bc])/(?P<video_id>\d+))?")


def valid_rtmp_stream(info):
    return all(key in info for key in REQUIRED_RTMP_KEYS)


class UsherService(object):
    def __init__(self, host="justin.tv"):
        self.host = host

    def url(self, path, *args, **kwargs):
        path = path.format(*args, **kwargs)
        return urljoin("http://usher." + self.host, path)

    def find(self, channel, password=None, **extra_params):
        url = self.url(USHER_FIND_PATH, channel)
        params = dict(p=int(random() * 999999), type="any",
                      private_code=password or "null", **extra_params)

        return res_json(urlget(url, params=params),
                        "stream info JSON")

    def create_playlist_token(self, channel):
        url = self.url(HLS_TOKEN_PATH, channel)
        params = dict(type="iphone", allow_cdn="true")

        try:
            res = urlget(url, params=params, exception=IOError)
        except IOError:
            return None

        json = res_json(res, "stream token JSON")

        if not (isinstance(json, list) and json):
            raise PluginError("Invalid JSON response")

        token = verifyjson(json[0], "token")
        hashed = hmac.new(HLS_TOKEN_KEY,
                          bytes(token, "utf8"),
                          sha1)

        return "{0}:{1}".format(hashed.hexdigest(), token)

    def create_playlist_url(self, channel):
        token = self.create_playlist_token(channel)

        if token:
            return self.url(HLS_PLAYLIST_PATH, channel, quote(token))


class JustinTVBase(Plugin):
    options = Options({
        "cookie": None,
        "password": None,
        "legacy-names": False
    })

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "mobile_justintv"

        return Plugin.stream_weight(key)

    def __init__(self, url):
        Plugin.__init__(self, url)

        try:
            match = re.match(URL_PATTERN, url).groupdict()
            self.channel = match.get("channel").lower()
            self.video_type = match.get("video_type")
            self.video_id = match.get("video_id")
            self.usher = UsherService(match.get("domain"))
        except AttributeError:
            self.channel = None
            self.video_id = None
            self.video_type = None
            self.usher = None

    # The HTTP support in rtmpdump's SWF verification is extremely
    # basic and does not support redirects, so we do the verifiction
    # ourselves instead. Also caches the result so we don't need
    # to do this every time.
    def _verify_swf(self, url):
        swfurl = urlresolve(url)

        # For some reason the URL returned sometimes contain random
        # user-agent/referer query parameters, let's strip them
        # so we actually cache.
        if "?" in url:
            swfurl = swfurl[:swfurl.find("?")]

        cache_key = "swf:{0}".format(swfurl)
        swfhash, swfsize = self.cache.get(cache_key, (None, None))

        if not (swfhash and swfsize):
            self.logger.debug("Verifying SWF")
            swfhash, swfsize = swfverify(swfurl)

            self.cache.set(cache_key, (swfhash, swfsize))

        return swfurl, swfhash, swfsize

    def _parse_find_result(self, res, swf):
        if not res:
            raise NoStreamsError(self.url)

        if not isinstance(res, list):
            raise PluginError("Invalid JSON response")

        streams = dict()
        swfurl, swfhash, swfsize = self._verify_swf(swf)

        for info in res:
            video_height = info.get("video_height")
            if self.options.get("legacy_names") and video_height:
                name = "{0}p".format(video_height)

                if info.get("type") == "live":
                    name += "+"
            else:
                name = info.get("display") or info.get("type")

            name = name.lower()
            if not valid_rtmp_stream(info):
                if info.get("needed_info") in ("chansub", "channel_subscription"):
                    self.logger.warning("The quality '{0}' is not available "
                                        "since it requires a subscription.",
                                        name)
                continue

            url = "{0}/{1}".format(info.get("connect"),
                                   info.get("play"))
            params = dict(rtmp=url, live=True, jtv=info.get("token"),
                          swfUrl=swfurl, swfhash=swfhash, swfsize=swfsize)

            stream = RTMPStream(self.session, params)
            streams[name] = stream

        return streams

    def _get_mobile_streams(self):
        url = self.usher.create_playlist_url(self.channel)

        if not url:
            raise NoStreamsError(self.url)

        try:
            streams = HLSStream.parse_variant_playlist(self.session, url,
                                                       nameprefix="mobile_")
        except IOError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise PluginError(err)

        return streams

    def _create_playlist_streams(self, videos):
        start_offset = int(videos.get("start_offset", 0))
        stop_offset = int(videos.get("end_offset", 0))
        streams = {}

        for quality, chunks in videos.get("chunks").items():
            # Rename 'live' to 'source'
            if quality == "live":
                quality = "source"

            if not chunks:
                if videos.get("restrictions", {}).get(quality) == "chansub":
                    self.logger.warning("The quality '{0}' is not available "
                                        "since it requires a subscription.",
                                        quality)
                continue

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
                headers = extract_flv_header_tags(chunk_stream)

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
            raise NoStreamsError(self.url)

        if self.video_id:
            return self._get_video_streams()
        else:
            return self._get_live_streams()

    def _get_live_streams(self, *args, **kwargs):
        streams = defaultdict(list)

        if RTMPStream.is_usable(self.session):
            try:
                for name, stream in self._get_desktop_streams(*args, **kwargs).items():
                    streams[name].append(stream)

            except PluginError as err:
                self.logger.error("Error when fetching desktop streams: {0}",
                                  err)
            except NoStreamsError:
                pass
        else:
            self.logger.warning("rtmpdump is required to access the desktop "
                                "streams, but it could not be found")

        try:
            for name, stream in self._get_mobile_streams(*args, **kwargs).items():
                # Justin.tv streams have a iphone prefix, so let's
                # strip it to keep it consistent with Twitch.
                name = name.replace("iphone", "")
                streams[name].append(stream)

        except PluginError as err:
            self.logger.error("Error when fetching mobile streams: {0}",
                              err)
        except NoStreamsError:
            pass

        return streams

    def _get_video_streams(self):
        pass
