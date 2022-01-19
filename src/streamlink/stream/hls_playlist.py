import logging
import math
import re
from binascii import unhexlify
from datetime import datetime, timedelta
from itertools import starmap
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Type, Union
from urllib.parse import urljoin, urlparse

# noinspection PyPackageRequirements
from isodate import ISO8601Error, parse_datetime

log = logging.getLogger(__name__)


class Resolution(NamedTuple):
    width: int
    height: int


# EXTINF
class ExtInf(NamedTuple):
    duration: float  # version >= 3: float
    title: Optional[str]


# EXT-X-BYTERANGE
class ByteRange(NamedTuple):  # version >= 4
    range: int
    offset: Optional[int]


# EXT-X-DATERANGE
class DateRange(NamedTuple):
    id: Optional[str]
    classname: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    duration: Optional[timedelta]
    planned_duration: Optional[timedelta]
    end_on_next: bool
    x: Dict[str, str]


# EXT-X-KEY
class Key(NamedTuple):
    method: str
    uri: str
    iv: Optional[bytes]  # version >= 2
    key_format: Optional[str]  # version >= 5
    key_format_versions: Optional[str]  # version >= 5


# EXT-X-MAP
class Map(NamedTuple):
    uri: str
    byterange: Optional[ByteRange]


# EXT-X-MEDIA
class Media(NamedTuple):
    uri: str
    type: str
    group_id: str
    language: Optional[str]
    name: str
    default: bool
    autoselect: bool
    forced: bool
    characteristics: Optional[str]


# EXT-X-START
class Start(NamedTuple):
    time_offset: float
    precise: bool


# EXT-X-STREAM-INF
class StreamInfo(NamedTuple):
    bandwidth: int
    program_id: Optional[str]  # version < 6
    codecs: List[str]
    resolution: Optional[Resolution]
    audio: Optional[str]
    video: Optional[str]
    subtitles: Optional[str]


# EXT-X-I-FRAME-STREAM-INF
class IFrameStreamInfo(NamedTuple):
    bandwidth: int
    program_id: Optional[str]
    codecs: List[str]
    resolution: Optional[Resolution]
    video: Optional[str]


class Playlist(NamedTuple):
    uri: str
    stream_info: Union[StreamInfo, IFrameStreamInfo]
    media: List[Media]
    is_iframe: bool


class Segment(NamedTuple):
    uri: str
    duration: float
    title: Optional[str]
    key: Optional[Key]
    discontinuity: bool
    byterange: Optional[ByteRange]
    date: Optional[datetime]
    map: Optional[Map]


class M3U8:
    def __init__(self):
        self.is_endlist: bool = False
        self.is_master: bool = False

        self.allow_cache: Optional[bool] = None  # version < 7
        self.discontinuity_sequence: Optional[int] = None
        self.iframes_only: Optional[bool] = None  # version >= 4
        self.media_sequence: Optional[int] = None
        self.playlist_type: Optional[str] = None
        self.target_duration: Optional[int] = None
        self.start: Optional[Start] = None
        self.version: Optional[int] = None

        self.media: List[Media] = []
        self.playlists: List[Playlist] = []
        self.dateranges: List[DateRange] = []
        self.segments: List[Segment] = []

    @classmethod
    def is_date_in_daterange(cls, date: Segment.date, daterange: DateRange):
        if date is None or daterange.start_date is None:
            return None

        if daterange.end_date is not None:
            return daterange.start_date <= date < daterange.end_date

        duration = daterange.duration or daterange.planned_duration
        if duration is not None:
            end = daterange.start_date + duration
            return daterange.start_date <= date < end

        return daterange.start_date <= date


class M3U8Parser:
    _extinf_re = re.compile(r"(?P<duration>\d+(\.\d+)?)(,(?P<title>.+))?")
    _attr_re = re.compile(r"([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|\"(.+?)\"|[0-9A-z\-]+)")
    _range_re = re.compile(r"(?P<range>\d+)(?:@(?P<offset>\d+))?")
    _tag_re = re.compile(r"#(?P<tag>[\w-]+)(:(?P<value>.+))?")
    _res_re = re.compile(r"(\d+)x(\d+)")

    def __init__(self, base_uri: Optional[str] = None, m3u8: Type[M3U8] = M3U8):
        self.base_uri: Optional[str] = base_uri
        self.m3u8: M3U8 = m3u8()
        self.state: Dict[str, Any] = {}

    def create_stream_info(self, streaminf: Dict[str, Optional[str]], cls=None):
        program_id = streaminf.get("PROGRAM-ID")

        bandwidth = streaminf.get("BANDWIDTH")
        if bandwidth:
            bandwidth = round(int(bandwidth), 1 - int(math.log10(int(bandwidth))))

        resolution = streaminf.get("RESOLUTION")
        if resolution:
            resolution = self.parse_resolution(resolution)

        codecs = streaminf.get("CODECS", "").split(",")

        if cls == IFrameStreamInfo:
            return IFrameStreamInfo(
                bandwidth,
                program_id,
                codecs,
                resolution,
                streaminf.get("VIDEO")
            )
        else:
            return StreamInfo(
                bandwidth,
                program_id,
                codecs,
                resolution,
                streaminf.get("AUDIO"),
                streaminf.get("VIDEO"),
                streaminf.get("SUBTITLES")
            )

    def split_tag(self, line):
        match = self._tag_re.match(line)

        if match:
            return match.group("tag"), (match.group("value") or "").strip()

        return None, None

    @staticmethod
    def map_attribute(key: str, value: str, quoted: str) -> Tuple[str, str]:
        return key, quoted or value

    def parse_attributes(self, value: str) -> Dict[str, str]:
        return dict(starmap(self.map_attribute, self._attr_re.findall(value)))

    @staticmethod
    def parse_bool(value: str) -> bool:
        return value == "YES"

    def parse_byterange(self, value: str) -> Optional[ByteRange]:
        match = self._range_re.match(value)
        if match is None:
            return None
        _range, offset = match.groups()
        return ByteRange(int(_range), int(offset) if offset is not None else None)

    def parse_extinf(self, value: str) -> Tuple[float, Optional[str]]:
        match = self._extinf_re.match(value)
        return ExtInf(0, None) if match is None else ExtInf(float(match.group("duration")), match.group("title"))

    @staticmethod
    def parse_hex(value: Optional[str]) -> Optional[bytes]:
        if value is None:
            return value

        value = value[2:]
        if len(value) % 2:
            value = "0" + value

        return unhexlify(value)

    @staticmethod
    def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
        try:
            return None if value is None else parse_datetime(value)
        except (ISO8601Error, ValueError):
            return None

    @staticmethod
    def parse_timedelta(value: Optional[str]) -> Optional[timedelta]:
        return None if value is None else timedelta(seconds=float(value))

    def parse_resolution(self, value: str) -> Resolution:
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

    def parse(self, data: str) -> M3U8:
        lines = iter(filter(bool, data.splitlines()))
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

    def uri(self, uri: str) -> str:
        if uri and urlparse(uri).scheme:
            return uri
        elif self.base_uri and uri:
            return urljoin(self.base_uri, uri)
        else:
            return uri

    def get_segment(self, uri: str) -> Segment:
        extinf: ExtInf = self.state.pop("extinf", None) or ExtInf(0, None)
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

    def get_playlist(self, uri: str) -> Playlist:
        streaminf = self.state.pop("streaminf", {})
        stream_info = self.create_stream_info(streaminf)
        return Playlist(uri, stream_info, [], False)


def load(data: str, base_uri: Optional[str] = None, parser: Type[M3U8Parser] = M3U8Parser, **kwargs) -> M3U8:
    """Attempts to parse a M3U8 playlist from a string of data.

    If specified, *base_uri* is the base URI that relative URIs will
    be joined together with, otherwise relative URIs will be as is.

    If specified, *parser* can be a M3U8Parser subclass to be used
    to parse the data.

    """
    return parser(base_uri, **kwargs).parse(data)
