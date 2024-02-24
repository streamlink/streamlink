from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, NamedTuple, Optional, Union

from streamlink.stream.segmented.segment import Segment


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
    uri: Optional[str]
    iv: Optional[bytes]  # version >= 2
    key_format: Optional[str]  # version >= 5
    key_format_versions: Optional[str]  # version >= 5


# EXT-X-MAP
class Map(NamedTuple):
    uri: str
    key: Optional[Key]
    byterange: Optional[ByteRange]


# EXT-X-MEDIA
class Media(NamedTuple):
    uri: Optional[str]
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


@dataclass
class HLSPlaylist:
    uri: str
    stream_info: Union[StreamInfo, IFrameStreamInfo]
    media: List[Media]
    is_iframe: bool


@dataclass
class HLSSegment(Segment):
    title: Optional[str]
    key: Optional[Key]
    discontinuity: bool
    byterange: Optional[ByteRange]
    date: Optional[datetime]
    map: Optional[Map]
