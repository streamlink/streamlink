import json
import re

from functools import reduce

from streamlink.compat import urlparse, range
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream, RTMPStream
from streamlink.stream.playlist import FLVPlaylist

COOKIES = {
    "family_filter": "off",
    "ff": "off"
}
QUALITY_MAP = {
    "ld": "240p",
    "sd": "360p",
    "hq": "480p",
    "hd720": "720p",
    "hd1080": "1080p",
    "custom": "live",
    "auto": "hds",
    "source": "hds"
}
STREAM_INFO_URL = "http://www.dailymotion.com/sequence/full/{0}"
USER_INFO_URL = "https://api.dailymotion.com/user/{0}"

_rtmp_re = re.compile(r"""
    (?P<host>rtmp://[^/]+)
    /(?P<app>[^/]+)
    /(?P<playpath>.+)
""", re.VERBOSE)
_url_re = re.compile(r"""
    http(s)?://(\w+\.)?
    dailymotion.com
    (?:
        (/embed)?/(video|live)
        /(?P<media_id>[^_?/]+)
    |
        /(?P<channel_name>[A-Za-z0-9-_]+)
    )
""", re.VERBOSE)
username_re = re.compile(r'''data-username\s*=\s*"(.*?)"''')
chromecast_re = re.compile(r'''stream_chromecast_url"\s*:\s*(?P<url>".*?")''')

_media_inner_schema = validate.Schema([{
    "layerList": [{
        "name": validate.text,
        validate.optional("sequenceList"): [{
            "layerList": validate.all(
                [{
                    "name": validate.text,
                    validate.optional("param"): dict
                }],
                validate.filter(lambda l: l["name"] in ("video", "reporting"))
            )
        }]
    }]
}])
_media_schema = validate.Schema(
    validate.any(
        _media_inner_schema,
        validate.all(
            {"sequence": _media_inner_schema},
            validate.get("sequence")
        )
    )
)
_vod_playlist_schema = validate.Schema({
    "duration": float,
    "fragments": [[int, float]],
    "template": validate.text
})
_vod_manifest_schema = validate.Schema({
    "alternates": [{
        "height": int,
        "template": validate.text,
        validate.optional("failover"): [validate.text]
    }]
})


class DailyMotion(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams_from_media(self, media_id):
        res = http.get(STREAM_INFO_URL.format(media_id), cookies=COOKIES)
        media = http.json(res, schema=_media_schema)

        params = extra_params = swf_url = None
        for __ in media:
            for __ in __["layerList"]:
                for __ in __.get("sequenceList", []):
                    for layer in __["layerList"]:
                        name = layer["name"]
                        if name == "video":
                            params = layer.get("param")
                        elif name == "reporting":
                            extra_params = layer.get("param", {})
                            extra_params = extra_params.get("extraParams", {})

        if not params:
            return

        if extra_params:
            swf_url = extra_params.get("videoSwfURL")

        mode = params.get("mode")
        if mode == "live":
            return self._get_live_streams(params, swf_url)
        elif mode == "vod":
            return self._get_vod_streams(params)

    def _get_live_streams(self, params, swf_url):
        for key, quality in QUALITY_MAP.items():
            key_url = "{0}URL".format(key)
            url = params.get(key_url)

            if not url:
                continue

            try:
                res = http.get(url, exception=IOError)
            except IOError:
                continue

            if quality == "hds":
                self.logger.debug('PLAYLIST URL: {0}'.format(res.url))
                try:
                    streams = HDSStream.parse_manifest(self.session, res.url)
                except:
                    streams = HLSStream.parse_variant_playlist(self.session, res.url)

                for name, stream in streams.items():
                    if key == "source":
                        name += "+"

                    yield name, stream
            elif res.text.startswith("rtmp"):
                match = _rtmp_re.match(res.text)
                if not match:
                    continue

                stream = RTMPStream(self.session, {
                    "rtmp": match.group("host"),
                    "app": match.group("app"),
                    "playpath": match.group("playpath"),
                    "swfVfy": swf_url,
                    "live": True
                })

                yield quality, stream

    def _create_flv_playlist(self, template):
        res = http.get(template)
        playlist = http.json(res, schema=_vod_playlist_schema)

        parsed = urlparse(template)
        url_template = "{0}://{1}{2}".format(
            parsed.scheme, parsed.netloc, playlist["template"]
        )
        segment_max = reduce(lambda i, j: i + j[0], playlist["fragments"], 0)

        substreams = [HTTPStream(self.session,
                                 url_template.replace("$fragment$", str(i)))
                      for i in range(1, segment_max + 1)]

        return FLVPlaylist(self.session,
                           duration=playlist["duration"],
                           flatten_timestamps=True,
                           skip_header=True,
                           streams=substreams)

    def _get_vod_streams(self, params):
        manifest_url = params.get("autoURL")
        if not manifest_url:
            return

        res = http.get(manifest_url)
        if res.headers.get("Content-Type") == "application/f4m+xml":
            streams = HDSStream.parse_manifest(self.session, res.url)

            # TODO: Replace with "yield from" when dropping Python 2.
            for __ in streams.items():
                yield __
        elif res.headers.get("Content-Type") == "application/vnd.apple.mpegurl":
            streams = HLSStream.parse_variant_playlist(self.session, res.url)

            # TODO: Replace with "yield from" when dropping Python 2.
            for __ in streams.items():
                yield __
        else:
            manifest = http.json(res, schema=_vod_manifest_schema)
            for params in manifest["alternates"]:
                name = "{0}p".format(params["height"])
                stream = self._create_flv_playlist(params["template"])
                yield name, stream

                failovers = params.get("failover", [])
                for failover in failovers:
                    stream = self._create_flv_playlist(failover)
                    yield name, stream

    def _chrome_cast_stream_fallback(self):
        self.logger.debug("Trying to find Chromecast URL as a fallback")
        # get the page if not already available
        page = http.get(self.url, cookies=COOKIES)
        m = chromecast_re.search(page.text)
        if m:
            url = json.loads(m.group("url"))
            return HLSStream.parse_variant_playlist(self.session, url)

    def get_featured_video(self):
        self.logger.debug("Channel page, attempting to play featured video")
        page = http.get(self.url, cookies=COOKIES)
        username_m = username_re.search(page.text)
        username = username_m and username_m.group(1)
        if username:
            self.logger.debug("Found username: {0}", username)
            res = http.get(USER_INFO_URL.format(username),
                           params={"fields": "videostar.url"})

            data = http.json(res)
            if "videostar.url" in data and self.can_handle_url(data["videostar.url"]):
                return data["videostar.url"]

    def _get_streams(self):
        match = _url_re.match(self.url)
        media_id = match.group("media_id")

        if not media_id and match.group("channel_name"):
            self.url = self.get_featured_video()
            match = _url_re.match(self.url)
            media_id = match.group("media_id")

        if media_id:
            self.logger.debug("Found media ID: {0}", media_id)
            streams = list(self._get_streams_from_media(media_id))
            if streams:
                return streams

        return self._chrome_cast_stream_fallback()


__plugin__ = DailyMotion
