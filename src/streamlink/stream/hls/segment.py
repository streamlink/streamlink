from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple

from streamlink.stream.segmented.segment import Segment


class Resolution(NamedTuple):
    width: int
    height: int


# EXTINF
class ExtInf(NamedTuple):
    duration: float  # version >= 3: float
    title: str | None


# EXT-X-BYTERANGE
class ByteRange(NamedTuple):  # version >= 4
    range: int
    offset: int | None


# EXT-X-DATERANGE
class DateRange(NamedTuple):
    id: str | None
    classname: str | None
    start_date: datetime | None
    end_date: datetime | None
    duration: timedelta | None
    planned_duration: timedelta | None
    end_on_next: bool
    x: dict[str, str]


# EXT-X-KEY
class Key(NamedTuple):
    method: str
    uri: str | None
    iv: bytes | None  # version >= 2
    key_format: str | None  # version >= 5
    key_format_versions: str | None  # version >= 5


# EXT-X-MAP
class Map(NamedTuple):
    uri: str
    key: Key | None
    byterange: ByteRange | None


# EXT-X-MEDIA
class Media(NamedTuple):
    uri: str | None
    type: str
    group_id: str
    language: str | None
    name: str
    default: bool
    autoselect: bool
    forced: bool
    characteristics: str | None


# EXT-X-START
class Start(NamedTuple):
    time_offset: float
    precise: bool


# EXT-X-STREAM-INF
class StreamInfo(NamedTuple):
    bandwidth: int
    program_id: str | None  # version < 6
    codecs: list[str]
    resolution: Resolution | None
    audio: str | None
    video: str | None
    subtitles: str | None


# EXT-X-I-FRAME-STREAM-INF
class IFrameStreamInfo(NamedTuple):
    bandwidth: int
    program_id: str | None
    codecs: list[str]
    resolution: Resolution | None
    video: str | None


@dataclass
class HLSPlaylist:
    uri: str
    stream_info: StreamInfo | IFrameStreamInfo
    media: list[Media]
    is_iframe: bool


@dataclass
class HLSSegment(Segment):
    title: str | None
    key: Key | None
    discontinuity: bool
    byterange: ByteRange | None
    date: datetime | None
    map: Map | None
