from livestreamer.compat import str, bytes, urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.options import Options
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HLSStream
from livestreamer.utils import (urlget, urlopen, swfverify, urlresolve, verifyjson,
                               res_json, res_xml)

from hashlib import sha1

import hmac
import random

class JustinTV(Plugin):
    options = Options({
        "cookie": None
    })

    APIBaseURL = "http://usher.justin.tv"
    StreamInfoURL = APIBaseURL + "/find/{0}.json"
    MetadataURL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
    SWFURL = "http://www.justin.tv/widgets/live_embed_player.swf"

    HLSStreamTokenKey = b"Wd75Yj9sS26Lmhve"
    HLSStreamTokenURL = APIBaseURL + "/stream/iphone_token/{0}.json"
    HLSPlaylistURL = APIBaseURL + "/stream/multi_playlist/{0}.m3u8"
    HLSTranscodeRequest = APIBaseURL + "/stream/transcode_iphone.json"

    @classmethod
    def can_handle_url(self, url):
        return ("justin.tv" in url) or ("twitch.tv" in url)

    def _get_channel_name(self, url):
        parts = urlparse(url).path.split("/")

        if len(parts) >= 2 and len(parts[1]) > 0:
            return parts[1].lower()

    def _get_metadata(self):
        url = self.MetadataURL.format(self.channelname)

        cookies = {}

        for cookie in self.options.get("cookie").split(";"):
            try:
                name, value = cookie.split("=")
            except ValueError:
                continue

            cookies[name.strip()] = value.strip()

        res = urlget(url, cookies=cookies)
        meta = res_xml(res, "metadata XML")

        metadata = {}
        metadata["access_guid"] = meta.findtext("access_guid")
        metadata["login"] = meta.findtext("login")
        metadata["title"] = meta.findtext("title")

        return metadata

    def _authenticate(self):
        if self.options.get("cookie") is not None:
            self.logger.info("Attempting to authenticate using cookies")

            metadata = self._get_metadata()
            chansub = metadata.get("access_guid")
            login = metadata.get("login")

            if login:
                self.logger.info("Successfully logged in as {0}", login)

            return chansub

    # The HTTP support in rtmpdump's SWF verification is extremly
    # basic, therefore we have to work around it.
    #
    # At first it seemed like resolving the 302 redirect was enough,
    # but it seems the resolved URLs also redirects sometimes causing
    # rtmpdump to fail. Safest to just to do the verification ourself.
    def _verify_swf(self):
        swfurl = urlresolve(self.SWFURL)

        # For some reason the URL returned sometimes contain random
        # user-agent/referer query parameters, let's strip them
        # so we actually cache.
        if "?" in swfurl:
            swfurl = swfurl[:swfurl.find("?")]

        cachekey = "swf:{0}".format(swfurl)
        swfhash, swfsize = self.cache.get(cachekey, (None, None))

        if not (swfhash and swfsize):
            self.logger.debug("Verifying SWF")
            swfhash, swfsize = swfverify(swfurl)

            self.cache.set(cachekey, (swfhash, swfsize))

        return swfurl, swfhash, swfsize

    def _get_rtmp_streams(self):
        chansub = self._authenticate()

        url = self.StreamInfoURL.format(self.channelname)
        params = dict(b_id="true", group="", private_code="null",
                      p=int(random.random() * 999999),
                      channel_subscription=chansub, type="any")

        self.logger.debug("Fetching stream info")
        res = urlget(url, params=params)
        json = res_json(res, "stream info JSON")

        if not isinstance(json, list):
            raise PluginError("Invalid JSON response")

        if len(json) == 0:
            raise NoStreamsError(self.url)

        streams = {}
        swfurl, swfhash, swfsize = self._verify_swf()

        for info in json:
            if not ("connect" in info and "play" in info
                    and "type" in info):

                continue

            stream = RTMPStream(self.session, {
                "rtmp": ("{0}/{1}").format(info["connect"], info["play"]),
                "swfUrl": swfurl,
                "swfhash": swfhash,
                "swfsize": swfsize,
                "live": True
            })

            if "display" in info:
                sname = info["display"]
            else:
                sname = info["type"]

            if "token" in info:
                stream.params["jtv"] = info["token"]
            else:
                self.logger.warning("No token found for stream {0}, this stream may fail to play", sname)

            streams[sname] = stream

        return streams

    def _get_hls_streams(self):
        url = self.HLSStreamTokenURL.format(self.channelname)

        try:
            res = urlget(url, params=dict(type="iphone", connection="wifi",
                         allow_cdn="true"), exception=IOError)
        except IOError:
            self.logger.debug("HLS streams not available")
            return {}

        json = res_json(res, "stream token JSON")

        if not isinstance(json, list):
            raise PluginError("Invalid JSON response")

        if len(json) == 0:
            raise PluginError("No stream token in JSON")

        token = verifyjson(json[0], "token")
        hashed = hmac.new(self.HLSStreamTokenKey, bytes(token, "utf8"), sha1)
        fulltoken = hashed.hexdigest() + ":" + token
        url = self.HLSPlaylistURL.format(self.channelname)

        try:
            params = dict(token=fulltoken, hd="true", allow_cdn="true")
            playlist = HLSStream.parse_variant_playlist(self.session, url,
                                                        nameprefix="mobile_",
                                                        params=params)
        except IOError as err:
            if "404" not in str(err):
                raise PluginError(err)
            else:
                self.logger.debug("Requesting mobile transcode")

                payload = dict(channel=self.channelname, type="iphone")
                urlopen(self.HLSTranscodeRequest, data=payload)

                return {}

        return playlist

    def _get_streams(self):
        self.channelname = self._get_channel_name(self.url)

        if not self.channelname:
            raise NoStreamsError(self.url)

        streams = {}

        if RTMPStream.is_usable(self.session):
            try:
                rtmpstreams = self._get_rtmp_streams()

                for name, stream in rtmpstreams.items():
                    if "iphone" in name:
                        name = name.replace("iphone", "mobile_")

                    streams[name] = stream
            except PluginError as err:
                self.logger.error("Error when fetching RTMP stream info: {0}", str(err))
        else:
            self.logger.warning("rtmpdump is not usable, only HLS streams will be available")

        try:
            hlsstreams = self._get_hls_streams()

            for name, stream in hlsstreams.items():
                if "iphone" in name:
                    name = name.replace("iphone", "mobile_")

                if name in streams:
                    streams[name] = [streams[name], stream]
                else:
                    streams[name] = stream

        except PluginError as err:
            self.logger.error("Error when fetching HLS stream info: {0}", str(err))

        return streams


__plugin__ = JustinTV
