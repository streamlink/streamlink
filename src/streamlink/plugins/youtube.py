import re

from requests import codes

from streamlink.compat import urlparse, parse_qsl
from streamlink.plugin import Plugin, PluginError, PluginArguments, PluginArgument
from streamlink.plugin.api import http, validate, useragents
from streamlink.plugin.api.utils import parse_query
from streamlink.stream import HTTPStream, HLSStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils import parse_json, search_dict

API_KEY = "AIzaSyBDBi-4roGzWJN4du9TuDMLd_jVTcVkKz4"
API_BASE = "https://www.googleapis.com/youtube/v3"
API_SEARCH_URL = API_BASE + "/search"
API_VIDEO_INFO = "https://youtube.com/get_video_info"
HLS_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def parse_stream_map(stream_map):
    if not stream_map:
        return []

    return [parse_query(s) for s in stream_map.split(",")]


def parse_fmt_list(formatsmap):
    formats = {}
    if not formatsmap:
        return formats

    for format in formatsmap.split(","):
        s = format.split("/")
        (w, h) = s[1].split("x")
        formats[int(s[0])] = "{0}p".format(h)

    return formats


_config_schema = validate.Schema(
    {
        validate.optional("fmt_list"): validate.all(
            validate.text,
            validate.transform(parse_fmt_list)
        ),
        validate.optional("url_encoded_fmt_stream_map"): validate.all(
            validate.text,
            validate.transform(parse_stream_map),
            [{
                "itag": validate.all(
                    validate.text,
                    validate.transform(int)
                ),
                "quality": validate.text,
                "url": validate.url(scheme="http"),
                validate.optional("s"): validate.text,
                validate.optional("stereo3d"): validate.all(
                    validate.text,
                    validate.transform(int),
                    validate.transform(bool)
                ),
            }]
        ),
        validate.optional("adaptive_fmts"): validate.all(
            validate.text,
            validate.transform(parse_stream_map),
            [{
                validate.optional("s"): validate.text,
                "type": validate.all(
                    validate.text,
                    validate.transform(lambda t: t.split(";")[0].split("/")),
                    [validate.text, validate.text]
                ),
                "url": validate.all(
                    validate.url(scheme="http")
                )
            }]
        ),
        validate.optional("hlsvp"): validate.text,
        validate.optional("live_playback"): validate.transform(bool),
        validate.optional("reason"): validate.text,
        validate.optional("livestream"): validate.text,
        validate.optional("live_playback"): validate.text,
        "status": validate.text
    }
)
_search_schema = validate.Schema(
    {
        "items": [{
            "id": {
                "videoId": validate.text
            }
        }]
    },
    validate.get("items")
)

_channelid_re = re.compile(r'meta itemprop="channelId" content="([^"]+)"')
_livechannelid_re = re.compile(r'meta property="og:video:url" content="([^"]+)')
_ytdata_re = re.compile(r'window\["ytInitialData"\]\s*=\s*({.*?});', re.DOTALL)
_url_re = re.compile(r"""
    http(s)?://(\w+\.)?youtube.com
    (?:
        (?:
            /(watch.+v=|embed/|v/)
            (?P<video_id>[0-9A-z_-]{11})
        )
        |
        (?:
            /(user|channel)/(?P<user>[^/?]+)
        )
        |
        (?:
            /(c/)?(?P<liveChannel>[^/?]+)/live
        )
    )
""", re.VERBOSE)


class YouTube(Plugin):
    adp_video = {
        137: "1080p",
        303: "1080p60",  # HFR
        299: "1080p60",  # HFR
        264: "1440p",
        308: "1440p60",  # HFR
        266: "2160p",
        315: "2160p60",  # HFR
        138: "2160p",
        302: "720p60",  # HFR
    }
    adp_audio = {
        140: 128,
        141: 256,
        171: 128,
        249: 48,
        250: 64,
        251: 160,
        256: 256,
        258: 258,
    }

    arguments = PluginArguments(
        PluginArgument(
            "api-key",
            sensitive=True,
            help="API key to use for YouTube API requests"
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        match_3d = re.match(r"(\w+)_3d", stream)
        match_hfr = re.match(r"(\d+p)(\d+)", stream)
        if match_3d:
            weight, group = Plugin.stream_weight(match_3d.group(1))
            weight -= 1
            group = "youtube_3d"
        elif match_hfr:
            weight, group = Plugin.stream_weight(match_hfr.group(1))
            weight += 1
            group = "high_frame_rate"
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, group

    def _create_adaptive_streams(self, info, streams, protected):
        adaptive_streams = {}
        best_audio_itag = None

        # Extract audio streams from the DASH format list
        for stream_info in info.get("adaptive_fmts", []):
            if stream_info.get("s"):
                protected = True
                continue

            stream_params = dict(parse_qsl(stream_info["url"]))
            if "itag" not in stream_params:
                continue
            itag = int(stream_params["itag"])
            # extract any high quality streams only available in adaptive formats
            adaptive_streams[itag] = stream_info["url"]

            stream_type, stream_format = stream_info["type"]
            if stream_type == "audio":
                stream = HTTPStream(self.session, stream_info["url"])
                name = "audio_{0}".format(stream_format)
                streams[name] = stream

                # find the best quality audio stream m4a, opus or vorbis
                if best_audio_itag is None or self.adp_audio[itag] > self.adp_audio[best_audio_itag]:
                    best_audio_itag = itag

        if best_audio_itag and adaptive_streams and MuxedStream.is_usable(self.session):
            aurl = adaptive_streams[best_audio_itag]
            for itag, name in self.adp_video.items():
                if itag in adaptive_streams:
                    vurl = adaptive_streams[itag]
                    self.logger.debug("MuxedStream: v {video} a {audio} = {name}".format(
                        audio=best_audio_itag,
                        name=name,
                        video=itag,
                    ))
                    streams[name] = MuxedStream(self.session,
                                                HTTPStream(self.session, vurl),
                                                HTTPStream(self.session, aurl))

        return streams, protected

    def _find_channel_video(self):
        res = http.get(self.url)

        datam = _ytdata_re.search(res.text)
        if datam:
            data = parse_json(datam.group(1))
            # find the videoRenderer object, where there is a LVE NOW badge
            for x in search_dict(data, 'videoRenderer'):
                for bstyle in search_dict(x.get("badges", {}), "style"):
                    if bstyle == "BADGE_STYLE_TYPE_LIVE_NOW":
                        if x.get("videoId"):
                            self.logger.debug("Found channel video ID via HTML: {0}", x["videoId"])
                            return x["videoId"]

        else:
            # fall back on API
            self.logger.debug("No channel data, falling back to API")
            match = _channelid_re.search(res.text)
            if not match:
                return

            channel_id = match.group(1)
            self.logger.debug("Found channel_id: {0}".format(channel_id))
            return self._get_channel_video(channel_id)

    def _get_channel_video(self, channel_id):
        query = {
            "channelId": channel_id,
            "type": "video",
            "eventType": "live",
            "part": "id",
            "key": self.get_option("api_key") or API_KEY
        }
        res = http.get(API_SEARCH_URL, params=query, raise_for_status=False)
        if res.status_code == codes.ok:
            videos = http.json(res, schema=_search_schema)

            for video in videos:
                video_id = video["id"]["videoId"]
                self.logger.debug("Found video_id: {0}".format(video_id))
                return video_id
        else:
            try:
                errors = http.json(res, exception=ValueError)
                self.logger.error("Cloud not resolve channel video:")
                for error in errors['error']['errors']:
                    self.logger.error("  {message} ({reason})".format(**error))

            except ValueError:
                self.logger.error("Cloud not resolve channel video: {0} error".format(res.status_code))

    def _find_canonical_stream_info(self):
        res = http.get(self.url)
        match = _livechannelid_re.search(res.text)
        if not match:
            return

        return self._get_stream_info(match.group(1))

    def _get_stream_info(self, url):
        match = _url_re.match(url)
        user = match.group("user")
        live_channel = match.group("liveChannel")

        if user:
            video_id = self._find_channel_video()
        elif live_channel:
            return self._find_canonical_stream_info()
        else:
            video_id = match.group("video_id")
            if video_id == "live_stream":
                query_info = dict(parse_qsl(urlparse(url).query))
                if "channel" in query_info:
                    video_id = self._get_channel_video(query_info["channel"])

        if not video_id:
            return

        # normal
        _params_1 = {"el": "detailpage"}
        # age restricted
        _params_2 = {"el": "embedded"}
        # embedded restricted
        _params_3 = {"eurl": "https://youtube.googleapis.com/v/{0}".format(video_id)}

        count = 0
        info_parsed = None
        for _params in (_params_1, _params_2, _params_3):
            count += 1
            params = {"video_id": video_id}
            params.update(_params)

            res = http.get(API_VIDEO_INFO, params=params, headers=HLS_HEADERS)
            info_parsed = parse_query(res.text, name="config", schema=_config_schema)
            if info_parsed.get("status") == "fail":
                self.logger.debug("get_video_info - {0}: {1}".format(
                    count, info_parsed.get("reason"))
                )
                continue
            self.logger.debug("get_video_info - {0}: Found data".format(count))
            break

        return info_parsed

    def _get_streams(self):
        http.headers.update({'User-Agent': useragents.CHROME})
        is_live = False

        info = self._get_stream_info(self.url)
        if not info:
            return

        if info.get("livestream") == '1' or info.get("live_playback") == '1':
            self.logger.debug("This video is live.")
            is_live = True

        formats = info.get("fmt_list")
        streams = {}
        protected = False
        for stream_info in info.get("url_encoded_fmt_stream_map", []):
            if stream_info.get("s"):
                protected = True
                continue

            stream = HTTPStream(self.session, stream_info["url"])
            name = formats.get(stream_info["itag"]) or stream_info["quality"]

            if stream_info.get("stereo3d"):
                name += "_3d"

            streams[name] = stream

        if not is_live:
            streams, protected = self._create_adaptive_streams(info, streams, protected)

        hls_playlist = info.get("hlsvp")
        if hls_playlist:
            try:
                hls_streams = HLSStream.parse_variant_playlist(
                    self.session, hls_playlist, headers=HLS_HEADERS, namekey="pixels"
                )
                streams.update(hls_streams)
            except IOError as err:
                self.logger.warning("Failed to extract HLS streams: {0}", err)

        if not streams and protected:
            raise PluginError("This plugin does not support protected videos, "
                              "try youtube-dl instead")

        return streams


__plugin__ = YouTube
