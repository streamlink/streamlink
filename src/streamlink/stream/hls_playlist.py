import re

from binascii import unhexlify
from collections import namedtuple
from itertools import starmap

from streamlink.compat import urljoin, urlparse

__all__ = ["load", "M3U8Parser"]


# EXT-X-BYTERANGE
ByteRange = namedtuple("ByteRange", "range offset")

# EXT-X-KEY
Key = namedtuple("Key", "method uri iv key_format key_format_versions")

# EXT-X-MAP
Map = namedtuple("Map", "uri byterange")

# EXT-X-MEDIA
Media = namedtuple("Media", "uri type group_id language name default "
                            "autoselect forced characteristics")

# EXT-X-START
Start = namedtuple("Start", "time_offset precise")

# EXT-X-STREAM-INF
StreamInfo = namedtuple("StreamInfo", "bandwidth program_id codecs resolution "
                                      "audio video subtitles")

# EXT-X-I-FRAME-STREAM-INF
IFrameStreamInfo = namedtuple("IFrameStreamInfo", "bandwidth program_id "
                                                  "codecs resolution video")

Playlist = namedtuple("Playlist", "uri stream_info media is_iframe")
Resolution = namedtuple("Resolution", "width height")
Segment = namedtuple("Segment", "uri duration title key discontinuity "
                                "byterange date map")

ATTRIBUTE_REGEX = (r"([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|"
                   r"\"(.+?)\"|[0-9A-z\-]+)")


class M3U8(object):
    def __init__(self):
        self.is_endlist = False
        self.is_master = False

        self.allow_cache = None
        self.discontinuity_sequence = None
        self.iframes_only = None
        self.media_sequence = None
        self.playlist_type = None
        self.target_duration = None
        self.start = None
        self.version = None

        self.media = []
        self.playlists = []
        self.segments = []


class M3U8Parser(object):
    def __init__(self, base_uri=None):
        self.base_uri = base_uri

    def create_stream_info(self, streaminf, cls=None):
        program_id = streaminf.get("PROGRAM-ID")

        bandwidth = streaminf.get("BANDWIDTH")
        if bandwidth:
            bandwidth = float(bandwidth)

        resolution = streaminf.get("RESOLUTION")
        if resolution:
            resolution = self.parse_resolution(resolution)

        codecs = streaminf.get("CODECS")
        if codecs:
            codecs = codecs.split(",")
        else:
            codecs = []

        if cls == IFrameStreamInfo:
            return IFrameStreamInfo(bandwidth, program_id, codecs, resolution,
                                    streaminf.get("VIDEO"))
        else:
            return StreamInfo(bandwidth, program_id, codecs, resolution,
                              streaminf.get("AUDIO"), streaminf.get("VIDEO"),
                              streaminf.get("SUBTITLES"))

    def split_tag(self, line):
        match = re.match("#(?P<tag>[\w-]+)(:(?P<value>.+))?", line)

        if match:
            return match.group("tag"), (match.group("value") or "").strip()

        return None, None

    def parse_attributes(self, value):
        def map_attribute(key, value, quoted):
            return (key, quoted or value)

        attr = re.findall(ATTRIBUTE_REGEX, value)

        return dict(starmap(map_attribute, attr))

    def parse_bool(self, value):
        return value == "YES"

    def parse_byterange(self, value):
        match = re.match("(?P<range>\d+)(@(?P<offset>.+))?", value)

        if match:
            return ByteRange(int(match.group("range")),
                             int(match.group("offset") or 0))

    def parse_extinf(self, value):
        match = re.match("(?P<duration>\d+(\.\d+)?)(,(?P<title>.+))?", value)
        if match:
            return float(match.group("duration")), match.group("title")
        return (0, None)

    def parse_hex(self, value):
        value = value[2:]
        if len(value) % 2:
            value = "0" + value

        return unhexlify(value)

    def parse_resolution(self, value):
        match = re.match("(\d+)x(\d+)", value)

        if match:
            width, height = int(match.group(1)), int(match.group(2))
        else:
            width, height = 0, 0

        return Resolution(width, height)

    def parse_tag(self, line, transform=None):
        tag, value = self.split_tag(line)

        if transform:
            value = transform(value)

        return value

    def parse_line(self, lineno, line):
        if lineno == 0 and not line.startswith("#EXTM3U"):
            raise ValueError("Missing #EXTM3U header")

        if not line.startswith("#"):
            if self.state.pop("expect_segment", None):
                byterange = self.state.pop("byterange", None)
                extinf = self.state.pop("extinf", (0, None))
                date = self.state.pop("date", None)
                map_ = self.state.get("map")
                key = self.state.get("key")

                segment = Segment(self.uri(line), extinf[0],
                                  extinf[1], key,
                                  self.state.pop("discontinuity", False),
                                  byterange, date, map_)
                self.m3u8.segments.append(segment)
            elif self.state.pop("expect_playlist", None):
                streaminf = self.state.pop("streaminf", {})
                stream_info = self.create_stream_info(streaminf)
                playlist = Playlist(self.uri(line), stream_info, [], False)
                self.m3u8.playlists.append(playlist)
        elif line.startswith("#EXTINF"):
            self.state["expect_segment"] = True
            self.state["extinf"] = self.parse_tag(line, self.parse_extinf)
        elif line.startswith("#EXT-X-BYTERANGE"):
            self.state["expect_segment"] = True
            self.state["byterange"] = self.parse_tag(line, self.parse_byterange)
        elif line.startswith("#EXT-X-TARGETDURATION"):
            self.m3u8.target_duration = self.parse_tag(line, int)
        elif line.startswith("#EXT-X-MEDIA-SEQUENCE"):
            self.m3u8.media_sequence = self.parse_tag(line, int)
        elif line.startswith("#EXT-X-KEY"):
            attr = self.parse_tag(line, self.parse_attributes)
            iv = attr.get("IV")
            if iv:
                iv = self.parse_hex(iv)
            self.state["key"] = Key(attr.get("METHOD"),
                                    self.uri(attr.get("URI")),
                                    iv, attr.get("KEYFORMAT"),
                                    attr.get("KEYFORMATVERSIONS"))
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME"):
            self.state["date"] = self.parse_tag(line)
        elif line.startswith("#EXT-X-ALLOW-CACHE"):
            self.m3u8.allow_cache = self.parse_tag(line, self.parse_bool)
        elif line.startswith("#EXT-X-STREAM-INF"):
            self.state["streaminf"] = self.parse_tag(line, self.parse_attributes)
            self.state["expect_playlist"] = True
        elif line.startswith("#EXT-X-PLAYLIST-TYPE"):
            self.m3u8.playlist_type = self.parse_tag(line)
        elif line.startswith("#EXT-X-ENDLIST"):
            self.m3u8.is_endlist = True
        elif line.startswith("#EXT-X-MEDIA"):
            attr = self.parse_tag(line, self.parse_attributes)
            media = Media(self.uri(attr.get("URI")), attr.get("TYPE"),
                          attr.get("GROUP-ID"), attr.get("LANGUAGE"),
                          attr.get("NAME"),
                          self.parse_bool(attr.get("DEFAULT")),
                          self.parse_bool(attr.get("AUTOSELECT")),
                          self.parse_bool(attr.get("FORCED")),
                          attr.get("CHARACTERISTICS"))
            self.m3u8.media.append(media)
        elif line.startswith("#EXT-X-DISCONTINUITY"):
            self.state["discontinuity"] = True
            self.state["map"] = None
        elif line.startswith("#EXT-X-DISCONTINUITY-SEQUENCE"):
            self.m3u8.discontinuity_sequence = self.parse_tag(line, int)
        elif line.startswith("#EXT-X-I-FRAMES-ONLY"):
            self.m3u8.iframes_only = True
        elif line.startswith("#EXT-X-MAP"):
            attr = self.parse_tag(line, self.parse_attributes)
            byterange = self.parse_byterange(attr.get("BYTERANGE", ""))
            self.state["map"] = Map(attr.get("URI"), byterange)
        elif line.startswith("#EXT-X-I-FRAME-STREAM-INF"):
            attr = self.parse_tag(line, self.parse_attributes)
            streaminf = self.state.pop("streaminf", attr)
            stream_info = self.create_stream_info(streaminf, IFrameStreamInfo)
            playlist = Playlist(self.uri(attr.get("URI")), stream_info, [], True)
            self.m3u8.playlists.append(playlist)
        elif line.startswith("#EXT-X-VERSION"):
            self.m3u8.version = self.parse_tag(line, int)
        elif line.startswith("#EXT-X-START"):
            attr = self.parse_tag(line, self.parse_attributes)
            start = Start(attr.get("TIME-OFFSET"),
                          self.parse_bool(attr.get("PRECISE", "NO")))
            self.m3u8.start = start

    def parse(self, data):
        self.state = {}
        self.m3u8 = M3U8()

        for lineno, line in enumerate(filter(bool, data.splitlines())):
            self.parse_line(lineno, line)

        # Associate Media entries with each Playlist
        for playlist in self.m3u8.playlists:
            for media_type in ("audio", "video", "subtitles"):
                group_id = getattr(playlist.stream_info, media_type, None)
                if group_id:
                    for media in filter(lambda m: m.group_id == group_id,
                                        self.m3u8.media):
                        playlist.media.append(media)

        self.m3u8.is_master = not not self.m3u8.playlists

        return self.m3u8

    def uri(self, uri):
        if uri and urlparse(uri).scheme:
            return uri
        elif self.base_uri and uri:
            return urljoin(self.base_uri, uri)
        else:
            return uri


def load(data, base_uri=None, parser=M3U8Parser):
    """Attempts to parse a M3U8 playlist from a string of data.

    If specified, *base_uri* is the base URI that relative URIs will
    be joined together with, otherwise relative URIs will be as is.

    If specified, *parser* can be a M3U8Parser subclass to be used
    to parse the data.

    """
    return parser(base_uri).parse(data)
