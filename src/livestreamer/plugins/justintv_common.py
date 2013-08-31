import hmac
import re

from collections import defaultdict
from hashlib import sha1
from random import random

from livestreamer.compat import bytes, quote, urljoin
from livestreamer.exceptions import NoStreamsError, PluginError
from livestreamer.options import Options
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HLSStream
from livestreamer.utils import (urlget, urlresolve,
                                swfverify, res_json, verifyjson)


__all__ = ["JustinTVBase"]

HLS_TOKEN_KEY = b"Wd75Yj9sS26Lmhve"
HLS_TOKEN_PATH = "/stream/iphone_token/{0}.json"
HLS_PLAYLIST_PATH = "/stream/multi_playlist/{0}.m3u8?token={1}&hd=true&allow_cdn=true"
USHER_FIND_PATH = "/find/{0}.json"
REQUIRED_RTMP_KEYS = ("connect", "play", "type", "token")
URL_PATTERN = r"http(s)?://([\w\.]+)?(?P<domain>twitch.tv|justin.tv)/(?P<channel>\w+)"


def valid_rtmp_stream(info):
    return all(key in info for key in REQUIRED_RTMP_KEYS)


class UsherService(object):
    def __init__(self, host="justin.tv"):
        self.host = host

    def url(self, path, *args, **kwargs):
        path = path.format(*args, **kwargs)
        return urljoin("http://usher." + self.host, path)

    def find(self, channel, **extra_params):
        url = self.url(USHER_FIND_PATH, channel)
        params = dict(p=int(random() * 999999), type="any",
                      private_code="null", **extra_params)

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
        "legacy-names": False
    })

    def __init__(self, url):
        Plugin.__init__(self, url)

        try:
            match = re.match(URL_PATTERN, url).groupdict()
            self.channel = match.get("channel").lower()
            self.usher = UsherService(match.get("domain"))
        except AttributeError:
            self.channel = None
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

        for info in filter(valid_rtmp_stream, res):
            if self.options.get("legacy_names"):
                video_height = info.get("video_height", 0)
                name = "{0}p".format(video_height)

                if info.get("type") == "live":
                    name += "+"
            else:
                name = info.get("display") or info.get("type")

            url = "{0}/{1}".format(info.get("connect"),
                                   info.get("play"))

            params = dict(rtmp=url, live=True, jtv=info.get("token"),
                          swfUrl=swfurl, swfhash=swfhash, swfsize=swfsize)

            stream = RTMPStream(self.session, params)
            streams[name.lower()] = stream

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

    def _get_streams(self):
        if not self.channel:
            raise NoStreamsError(self.url)

        streams = defaultdict(list)

        if RTMPStream.is_usable(self.session):
            try:
                for name, stream in self._get_desktop_streams().items():
                    streams[name].append(stream)

            except PluginError as err:
                self.logger.error("Error when fetching desktop streams: {0}",
                                  err)
            except NoStreamsError:
                pass
        else:
            self.logger.warning("rtmpdump is not usable, "
                                "only mobile streams may be available")

        try:
            for name, stream in self._get_mobile_streams().items():
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
