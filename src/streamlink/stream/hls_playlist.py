import logging
import math
import re
from binascii import unhexlify
from collections import namedtuple
from datetime import timedelta
from itertools import starmap

from isodate import ISO8601Error, parse_datetime
from requests import Response

from streamlink.compat import str, urljoin, urlparse

log = logging.getLogger(__name__)

__all__ = ["load", "M3U8Parser"]

# EXTINF
ExtInf = namedtuple("ExtInf", "duration title")

# EXT-X-BYTERANGE
ByteRange = namedtuple("ByteRange", "range offset")

# EXT-X-DATERANGE
DateRange = namedtuple("DateRange", "id classname start_date end_date duration planned_duration end_on_next x")

# EXT-X-KEY
Key = namedtuple("Key", "method uri iv key_format key_format_versions")

# EXT-X-MAP
Map = namedtuple("Map", "uri byterange")

# EXT-X-MEDIA
Media = namedtuple("Media", "uri type group_id language name default autoselect forced characteristics")

# EXT-X-START
Start = namedtuple("Start", "time_offset precise")

# EXT-X-STREAM-INF
StreamInfo = namedtuple("StreamInfo", "bandwidth program_id codecs resolution audio video subtitles")

# EXT-X-I-FRAME-STREAM-INF
IFrameStreamInfo = namedtuple("IFrameStreamInfo", "bandwidth program_id codecs resolution video")

Playlist = namedtuple("Playlist", "uri stream_info media is_iframe")
Resolution = namedtuple("Resolution", "width height")
Segment = namedtuple("Segment", "uri duration title key discontinuity byterange date map")


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
        self.dateranges = []
        self.segments = []

    @classmethod
    def is_date_in_daterange(cls, date, daterange):
        if date is None or daterange.start_date is None:
            return None

        if daterange.end_date is not None:
            return daterange.start_date <= date < daterange.end_date

        duration = daterange.duration or daterange.planned_duration
        if duration is not None:
            end = daterange.start_date + duration
            return daterange.start_date <= date < end

        return daterange.start_date <= date


class M3U8Parser(object):
    _extinf_re = re.compile(r"(?P<duration>\d+(\.\d+)?)(,(?P<title>.+))?")
    _attr_re = re.compile(r"([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|\"(.+?)\"|[0-9A-z\-]+)")
    _range_re = re.compile(r"(?P<range>\d+)(?:@(?P<offset>\d+))?")
    _tag_re = re.compile(r"#(?P<tag>[\w-]+)(:(?P<value>.+))?")
    _res_re = re.compile(r"(\d+)x(\d+)")

    def __init__(self, base_uri=None, m3u8=M3U8, **kwargs):
        self.base_uri = base_uri
        self.m3u8 = m3u8()
        self.state = {}

    def create_stream_info(self, streaminf, cls=None):
        program_id = streaminf.get("PROGRAM-ID")

        bandwidth = streaminf.get("BANDWIDTH")
        if bandwidth:
            bandwidth = round(int(bandwidth), 1 - int(math.log10(int(bandwidth))))

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
        match = self._tag_re.match(line)

        if match:
            return match.group("tag"), (match.group("value") or "").strip()

        return None, None

    @staticmethod
    def map_attribute(key, value, quoted):
        return key, quoted or value

    def parse_attributes(self, value):
        return dict(starmap(self.map_attribute, self._attr_re.findall(value)))

    @staticmethod
    def parse_bool(value):
        return value == "YES"

    def parse_byterange(self, value):
        match = self._range_re.match(value)
        if match is None:
            return None
        _range, offset = match.groups()
        return ByteRange(int(_range), int(offset) if offset is not None else None)

    def parse_extinf(self, value):
        match = self._extinf_re.match(value)
        return ExtInf(0, None) if match is None else ExtInf(float(match.group("duration")), match.group("title"))

    @staticmethod
    def parse_hex(value):
        if value is None:
            return value

        value = value[2:]
        if len(value) % 2:
            value = "0" + value

        return unhexlify(value)

    @staticmethod
    def parse_iso8601(value):
        try:
            return None if value is None else parse_datetime(value)
        except (ISO8601Error, ValueError):
            return None

    @staticmethod
    def parse_timedelta(value):
        return None if value is None else timedelta(seconds=float(value))

    def parse_resolution(self, value):
        match = self._res_re.match(value)

        if match:
            width, height = int(match.group(1)), int(match.group(2))
        else:
            width, height = 0, 0

        return Resolution(width, height)

    def parse_tag_extinf(self, value):
        self.state["expect_segment"] = True
        self.state["extinf"] = self.parse_extinf(value)

    def parse_tag_ext_x_byterange(self, value):
        self.state["expect_segment"] = True
        self.state["byterange"] = self.parse_byterange(value)

    def parse_tag_ext_x_targetduration(self, value):
        self.m3u8.target_duration = int(value)

    def parse_tag_ext_x_media_sequence(self, value):
        self.m3u8.media_sequence = int(value)

    def parse_tag_ext_x_key(self, value):
        attr = self.parse_attributes(value)
        self.state["key"] = Key(
            attr.get("METHOD"),
            self.uri(attr.get("URI")),
            self.parse_hex(attr.get("IV")),
            attr.get("KEYFORMAT"),
            attr.get("KEYFORMATVERSIONS")
        )

    def parse_tag_ext_x_program_date_time(self, value):
        self.state["date"] = self.parse_iso8601(value)

    def parse_tag_ext_x_daterange(self, value):
        attr = self.parse_attributes(value)
        daterange = DateRange(
            attr.pop("ID", None),
            attr.pop("CLASS", None),
            self.parse_iso8601(attr.pop("START-DATE", None)),
            self.parse_iso8601(attr.pop("END-DATE", None)),
            self.parse_timedelta(attr.pop("DURATION", None)),
            self.parse_timedelta(attr.pop("PLANNED-DURATION", None)),
            self.parse_bool(attr.pop("END-ON-NEXT", None)),
            attr
        )
        self.m3u8.dateranges.append(daterange)

    def parse_tag_ext_x_allow_cache(self, value):  # version < 7
        self.m3u8.allow_cache = self.parse_bool(value)

    def parse_tag_ext_x_stream_inf(self, value):
        self.state["streaminf"] = self.parse_attributes(value)
        self.state["expect_playlist"] = True

    def parse_tag_ext_x_playlist_type(self, value):
        self.m3u8.playlist_type = value

    # noinspection PyUnusedLocal
    def parse_tag_ext_x_endlist(self, value):
        self.m3u8.is_endlist = True

    def parse_tag_ext_x_media(self, value):
        attr = self.parse_attributes(value)
        media = Media(
            self.uri(attr.get("URI")),
            attr.get("TYPE"),
            attr.get("GROUP-ID"),
            attr.get("LANGUAGE"),
            attr.get("NAME"),
            self.parse_bool(attr.get("DEFAULT")),
            self.parse_bool(attr.get("AUTOSELECT")),
            self.parse_bool(attr.get("FORCED")),
            attr.get("CHARACTERISTICS")
        )
        self.m3u8.media.append(media)

    # noinspection PyUnusedLocal
    def parse_tag_ext_x_discontinuity(self, value):
        self.state["discontinuity"] = True
        self.state["map"] = None

    def parse_tag_ext_x_discontinuity_sequence(self, value):
        self.m3u8.discontinuity_sequence = int(value)

    # noinspection PyUnusedLocal
    def parse_tag_ext_x_i_frames_only(self, value):  # version >= 4
        self.m3u8.iframes_only = True

    def parse_tag_ext_x_map(self, value):  # version >= 5
        attr = self.parse_attributes(value)
        byterange = self.parse_byterange(attr.get("BYTERANGE", ""))
        self.state["map"] = Map(self.uri(attr.get("URI")), byterange)

    def parse_tag_ext_x_i_frame_stream_inf(self, value):
        attr = self.parse_attributes(value)
        streaminf = self.state.pop("streaminf", attr)
        stream_info = self.create_stream_info(streaminf, IFrameStreamInfo)
        playlist = Playlist(self.uri(attr.get("URI")), stream_info, [], True)
        self.m3u8.playlists.append(playlist)

    def parse_tag_ext_x_version(self, value):
        self.m3u8.version = int(value)

    def parse_tag_ext_x_start(self, value):
        attr = self.parse_attributes(value)
        self.m3u8.start = Start(
            float(attr.get("TIME-OFFSET", 0)),
            self.parse_bool(attr.get("PRECISE", "NO"))
        )

    def parse_line(self, line):
        if line.startswith("#"):
            tag, value = self.split_tag(line)
            if not tag:
                return
            method = "parse_tag_" + tag.lower().replace("-", "_")
            if not hasattr(self, method):
                return
            getattr(self, method)(value)
        elif self.state.pop("expect_segment", None):
            segment = self.get_segment(self.uri(line))
            self.m3u8.segments.append(segment)
        elif self.state.pop("expect_playlist", None):
            playlist = self.get_playlist(self.uri(line))
            self.m3u8.playlists.append(playlist)

    def parse(self, data):
        if isinstance(data, str):
            lines = iter(filter(bool, data.splitlines()))
        else:
            lines = iter(filter(bool, data.iter_lines(decode_unicode=True)))

        try:
            line = next(lines)
        except StopIteration:
            return self.m3u8
        else:
            if not line.startswith("#EXTM3U"):
                log.warning("Malformed HLS Playlist. Expected #EXTM3U, but got {0}".format(line[:250]))
                raise ValueError("Missing #EXTM3U header")

        parse_line = self.parse_line
        for line in lines:
            parse_line(line)

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

    def get_segment(self, uri):
        extinf = self.state.pop("extinf", (0, None))
        return Segment(
            uri,
            extinf.duration,
            extinf.title,
            self.state.get("key"),
            self.state.pop("discontinuity", False),
            self.state.pop("byterange", None),
            self.state.pop("date", None),
            self.state.get("map")
        )

    def get_playlist(self, uri):
        streaminf = self.state.pop("streaminf", {})
        stream_info = self.create_stream_info(streaminf)
        return Playlist(uri, stream_info, [], False)


def load(data, base_uri=None, parser=M3U8Parser, **kwargs):
    """
    Parse an M3U8 playlist from a string of data or an HTTP response.

    If specified, *base_uri* is the base URI that relative URIs will
    be joined together with, otherwise relative URIs will be as is.

    If specified, *parser* can be an M3U8Parser subclass to be used
    to parse the data.
    """
    if base_uri is None and isinstance(data, Response):
        base_uri = data.url

    return parser(base_uri, **kwargs).parse(data)
