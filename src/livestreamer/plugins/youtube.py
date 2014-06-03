import re

from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_json
from livestreamer.stream import HTTPStream, HLSStream
from livestreamer.utils import parse_qsd

API_KEY = "AIzaSyBDBi-4roGzWJN4du9TuDMLd_jVTcVkKz4"
API_BASE = "https://www.googleapis.com/youtube/v3"
API_SEARCH_URL = API_BASE + "/search"
HLS_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def parse_stream_map(streammap):
    streams = []
    if not streammap:
        return streams

    for stream_qs in streammap.split(","):
        stream = parse_qsd(stream_qs)
        streams.append(stream)

    return streams


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
        "args": {
            "fmt_list": validate.all(
                validate.text,
                validate.transform(parse_fmt_list)
            ),
            "url_encoded_fmt_stream_map": validate.all(
                validate.text,
                validate.transform(parse_stream_map),
                [{
                    "itag": validate.all(
                        validate.text,
                        validate.transform(int)
                    ),
                    "quality": validate.text,
                    "url": validate.text,
                    validate.optional("s"): validate.text,
                    validate.optional("stereo3d"): validate.all(
                        validate.text,
                        validate.transform(int),
                        validate.transform(bool)
                    ),
                }]
            ),
            validate.optional("hlsvp"): validate.text,
            validate.optional("live_playback"): validate.transform(bool),
        }
    },
    validate.get("args")
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

_url_re = re.compile("""
    http(s)?://(\w+.)?
    (youtube.com|youtu.be)
    (?:
        /(watch.+v=|embed/|v/)
        (?P<video_id>[^/?&]+)
    )?
    (?:
        (/user/)?(?P<user>[^/?]+)
    ?)
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

    def _find_config(self, data):
        match = re.search("'PLAYER_CONFIG': (.+)\n.+}\);", data)
        if match:
            return match.group(1)

        match = re.search("yt.playerConfig = (.+)\;\n", data)
        if match:
            return match.group(1)

        match = re.search("ytplayer.config = (.+);\(function", data)
        if match:
            return match.group(1)

        match = re.search("data-swf-config=\"(.+)\"", data)
        if match:
            config = match.group(1)
            config = config.replace("&amp;quot;", "\"")

            return config

    def _find_channel_config(self, data):
        match = re.search(r'meta itemprop="channelId" content="([^"]+)"', data)
        if not match:
            return

        channel_id = match.group(1)
        query = dict(channelId=channel_id, type="video", eventType="live",
                     part="id", key=API_KEY)
        res = http.get(API_SEARCH_URL, params=query)
        videos = http.json(res, schema=_search_schema)

        for video in videos:
            video_id = video["id"]["videoId"]
            url = "http://youtube.com/watch?v={0}".format(video_id)
            config = self._get_stream_info(url)
            if config:
                return config

    def _get_stream_info(self, url):
        match = re.search("/(embed|v)/([^?]+)", url)
        if match:
            url = "http://youtube.com/watch?v={0}".format(match.group(2))

        res = http.get(url)
        match = re.search("/user/([^?/]+)", res.url)
        if match:
            return self._find_channel_config(res.text)
        else:
            config = self._find_config(res.text)

        if config:
            return parse_json(config, "config JSON", schema=_config_schema)

    def _get_streams(self):
        info = self._get_stream_info(self.url)

        if not info:
            raise NoStreamsError(self.url)

        formats = info["fmt_list"]
        streams = {}
        for stream_info in info["url_encoded_fmt_stream_map"]:
            params = {}
            sig = stream_info.get("s")
            if sig:
                params["signature"] = self._decrypt_signature(sig)

            stream = HTTPStream(self.session, stream_info["url"], params=params)
            name = formats.get(stream_info["itag"]) or stream_info["quality"]

            if stream_info.get("stereo3d"):
                name += "_3d"

            streams[name] = stream

        hls_playlist = info.get("hlsvp")
        if hls_playlist:
            try:
                hls_streams = HLSStream.parse_variant_playlist(
                    self.session, hls_playlist, headers=HLS_HEADERS, namekey="pixels"
                )
                streams.update(hls_streams)
            except IOError as err:
                self.logger.warning("Failed to get HLS streams: {0}", err)

        if not streams and not info.get("live_playback"):
            self.logger.warning("VOD support may not be 100% complete. "
                                "Try youtube-dl instead.")

        return streams

    def _decrypt_signature(self, s):
        """Turn the encrypted s field into a working signature

        Source: https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py
        """

        if len(s) == 92:
            return s[25] + s[3:25] + s[0] + s[26:42] + s[79] + s[43:79] + s[91] + s[80:83]
        elif len(s) == 90:
            return s[25] + s[3:25] + s[2] + s[26:40] + s[77] + s[41:77] + s[89] + s[78:81]
        elif len(s) == 88:
            return s[48] + s[81:67:-1] + s[82] + s[66:62:-1] + s[85] + s[61:48:-1] + s[67] + s[47:12:-1] + s[3] + s[11:3:-1] + s[2] + s[12]
        elif len(s) == 87:
            return s[4:23] + s[86] + s[24:85]
        elif len(s) == 86:
            return s[83:85] + s[26] + s[79:46:-1] + s[85] + s[45:36:-1] + s[30] + s[35:30:-1] + s[46] + s[29:26:-1] + s[82] + s[25:1:-1]
        elif len(s) == 85:
            return s[2:8] + s[0] + s[9:21] + s[65] + s[22:65] + s[84] + s[66:82] + s[21]
        elif len(s) == 84:
            return s[83:36:-1] + s[2] + s[35:26:-1] + s[3] + s[25:3:-1] + s[26]
        elif len(s) == 83:
            return s[6] + s[3:6] + s[33] + s[7:24] + s[0] + s[25:33] + s[53] + s[34:53] + s[24] + s[54:]
        elif len(s) == 82:
            return s[36] + s[79:67:-1] + s[81] + s[66:40:-1] + s[33] + s[39:36:-1] + s[40] + s[35] + s[0] + s[67] + s[32:0:-1] + s[34]
        elif len(s) == 81:
            return s[56] + s[79:56:-1] + s[41] + s[55:41:-1] + s[80] + s[40:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
        elif len(s) == 79:
            return s[54] + s[77:54:-1] + s[39] + s[53:39:-1] + s[78] + s[38:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
        else:
            self.logger.warning("Unable to decrypt signature, key length {0} not supported; retrying might work", len(s))
            return None

__plugin__ = YouTube
