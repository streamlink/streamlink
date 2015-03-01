import re

from livestreamer.plugin import Plugin, PluginError
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_query
from livestreamer.stream import HTTPStream, HLSStream

API_KEY = "AIzaSyBDBi-4roGzWJN4du9TuDMLd_jVTcVkKz4"
API_BASE = "https://www.googleapis.com/youtube/v3"
API_SEARCH_URL = API_BASE + "/search"
API_VIDEO_INFO = "http://youtube.com/get_video_info"
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

_channelid_re = re.compile('meta itemprop="channelId" content="([^"]+)"')
_url_re = re.compile("""
    http(s)?://(\w+\.)?youtube.com
    (?:
        (?:
            /(watch.+v=|embed/|v/)
            (?P<video_id>[0-9A-z_-]{11})
        )
        |
        (?:
            /user/(?P<user>[^/?]+)
        )
    )
""", re.VERBOSE)


class YouTube(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        match = re.match("(\w+)_3d", stream)
        if match:
            weight, group = Plugin.stream_weight(match.group(1))
            weight -= 1
            group = "youtube_3d"
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, group

    def _find_channel_video(self):
        res = http.get(self.url)
        match = _channelid_re.search(res.text)
        if not match:
            return

        channel_id = match.group(1)
        query = {
            "channelId": channel_id,
            "type": "video",
            "eventType": "live",
            "part": "id",
            "key": API_KEY
        }
        res = http.get(API_SEARCH_URL, params=query)
        videos = http.json(res, schema=_search_schema)

        for video in videos:
            video_id = video["id"]["videoId"]
            return video_id

    def _get_stream_info(self, url):
        match = _url_re.match(url)
        user = match.group("user")

        if user:
            video_id = self._find_channel_video()
        else:
            video_id = match.group("video_id")

        if not video_id:
            return

        params = {
            "video_id": video_id,
            "el": "player_embedded"
        }
        res = http.get(API_VIDEO_INFO, params=params)

        return parse_query(res.text, name="config", schema=_config_schema)

    def _get_streams(self):
        info = self._get_stream_info(self.url)
        if not info:
            return

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

        # Extract audio streams from the DASH format list
        for stream_info in info.get("adaptive_fmts", []):
            if stream_info.get("s"):
                protected = True
                continue

            stream_type, stream_format = stream_info["type"]
            if stream_type != "audio":
                continue

            stream = HTTPStream(self.session, stream_info["url"])
            name = "audio_{0}".format(stream_format)

            streams[name] = stream

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
