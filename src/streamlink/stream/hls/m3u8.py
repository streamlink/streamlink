from __future__ import annotations

import logging
import math
import re
from binascii import Error as BinasciiError, unhexlify
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar
from urllib.parse import urljoin, urlparse

from isodate import ISO8601Error, parse_datetime  # type: ignore[import]
from requests import Response

from streamlink.logger import ALL, StreamlinkLogger
from streamlink.stream.hls.segment import (
    ByteRange,
    DateRange,
    ExtInf,
    HLSPlaylist,
    HLSSegment,
    IFrameStreamInfo,
    Key,
    Map,
    Media,
    Resolution,
    Start,
    StreamInfo,
)


if TYPE_CHECKING:
    try:
        from typing import Self  # type: ignore[attr-defined]
    except ImportError:
        from typing_extensions import Self


log: StreamlinkLogger = logging.getLogger(__name__)  # type: ignore[assignment]


THLSSegment_co = TypeVar("THLSSegment_co", bound=HLSSegment, covariant=True)
THLSPlaylist_co = TypeVar("THLSPlaylist_co", bound=HLSPlaylist, covariant=True)


class M3U8(Generic[THLSSegment_co, THLSPlaylist_co]):
    def __init__(self, uri: str | None = None):
        self.uri = uri

        self.is_endlist: bool = False
        self.is_master: bool = False

        self.allow_cache: bool | None = None  # version < 7
        self.discontinuity_sequence: int | None = None
        self.iframes_only: bool | None = None  # version >= 4
        self.media_sequence: int | None = None
        self.playlist_type: str | None = None
        self.targetduration: float | None = None
        self.start: Start | None = None
        self.version: int | None = None

        self.media: list[Media] = []
        self.dateranges: list[DateRange] = []

        self.playlists: list[THLSPlaylist_co] = []
        self.segments: list[THLSSegment_co] = []

    @classmethod
    def is_date_in_daterange(cls, date: datetime | None, daterange: DateRange):
        if date is None or daterange.start_date is None:
            return None

        if daterange.end_date is not None:
            return daterange.start_date <= date < daterange.end_date

        duration = daterange.duration or daterange.planned_duration
        if duration is not None:
            end = daterange.start_date + duration
            return daterange.start_date <= date < end

        return daterange.start_date <= date


TM3U8_co = TypeVar("TM3U8_co", bound=M3U8, covariant=True)


_symbol_tag_parser = "__PARSE_TAG_NAME"


def parse_tag(tag: str):
    def decorator(func: Callable[[str], None]) -> Callable[[str], None]:
        setattr(func, _symbol_tag_parser, tag)

        return func

    return decorator


class M3U8ParserMeta(type):
    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)

        tags = dict(**getattr(cls, "_TAGS", {}))
        for member in namespace.values():
            tag = getattr(member, _symbol_tag_parser, None)
            if type(tag) is not str:
                continue
            tags[tag] = member
        cls._TAGS = tags


class M3U8Parser(Generic[TM3U8_co, THLSSegment_co, THLSPlaylist_co], metaclass=M3U8ParserMeta):
    # Can't set type vars as classvars yet (PEP 526 issue)
    __m3u8__: ClassVar[type[M3U8[HLSSegment, HLSPlaylist]]] = M3U8
    __segment__: ClassVar[type[HLSSegment]] = HLSSegment
    __playlist__: ClassVar[type[HLSPlaylist]] = HLSPlaylist

    _TAGS: ClassVar[Mapping[str, Callable[[Self, str], None]]]

    _extinf_re = re.compile(r"(?P<duration>\d+(\.\d+)?)(,(?P<title>.+))?")
    _attr_re = re.compile(
        r"""
            (?P<key>[A-Z0-9\-]+)
            =
            (?P<value>
                (?# decimal-integer)
                \d+
                (?# hexadecimal-sequence)
                |0[xX][0-9A-Fa-f]+
                (?# decimal-floating-point and signed-decimal-floating-point)
                |-?\d+\.\d+
                (?# quoted-string)
                |\"(?P<quoted>[^\r\n\"]*)\"
                (?# enumerated-string)
                |[^\",\s]+
                (?# decimal-resolution)
                |\d+x\d+
            )
            (?# be more lenient and allow spaces around attributes)
            \s*(?:,\s*|$)
        """,
        re.VERBOSE,
    )
    _range_re = re.compile(r"(?P<range>\d+)(?:@(?P<offset>\d+))?")
    _tag_re = re.compile(r"#(?P<tag>[\w-]+)(:(?P<value>.+))?")
    _res_re = re.compile(r"(\d+)x(\d+)")

    def __init__(self, base_uri: str | None = None):
        self.m3u8: TM3U8_co = self.__m3u8__(base_uri)  # type: ignore[assignment]  # PEP 696 might solve this

        self._expect_playlist: bool = False
        self._streaminf: dict[str, str] | None = None

        self._expect_segment: bool = False
        self._extinf: ExtInf | None = None
        self._byterange: ByteRange | None = None
        self._discontinuity: bool = False
        self._map: Map | None = None
        self._key: Key | None = None
        self._date: datetime | None = None

    @classmethod
    def create_stream_info(cls, streaminf: Mapping[str, str | None], streaminfoclass=None):
        program_id = streaminf.get("PROGRAM-ID")

        try:
            bandwidth = int(streaminf.get("BANDWIDTH") or 0)
            bandwidth = round(bandwidth, 1 - int(math.log10(bandwidth)))
        except ValueError:
            bandwidth = 0

        res = streaminf.get("RESOLUTION")
        resolution = None if not res else cls.parse_resolution(res)

        codecs = (streaminf.get("CODECS") or "").split(",")

        if streaminfoclass is IFrameStreamInfo:
            return IFrameStreamInfo(
                bandwidth=bandwidth,
                program_id=program_id,
                codecs=codecs,
                resolution=resolution,
                video=streaminf.get("VIDEO"),
            )
        else:
            return StreamInfo(
                bandwidth=bandwidth,
                program_id=program_id,
                codecs=codecs,
                resolution=resolution,
                audio=streaminf.get("AUDIO"),
                video=streaminf.get("VIDEO"),
                subtitles=streaminf.get("SUBTITLES"),
            )

    @classmethod
    def split_tag(cls, line: str) -> tuple[str, str] | tuple[None, None]:
        match = cls._tag_re.match(line)

        if match:
            return match.group("tag"), (match.group("value") or "").strip()

        return None, None

    @classmethod
    def parse_attributes(cls, value: str) -> dict[str, str]:
        pos = 0
        length = len(value)
        res: dict[str, str] = {}
        while pos < length:
            match = cls._attr_re.match(value, pos)
            if match is None:
                log.warning("Discarded invalid attributes list")
                res.clear()
                break
            pos = match.end()
            res[match["key"]] = match["quoted"] if match["quoted"] is not None else match["value"]

        return res

    @staticmethod
    def parse_bool(value: str) -> bool:
        return value == "YES"

    @classmethod
    def parse_byterange(cls, value: str) -> ByteRange | None:
        match = cls._range_re.match(value)
        if match is None:
            return None

        offset = match["offset"]

        return ByteRange(
            range=int(match["range"]),
            offset=int(offset) if offset is not None else None,
        )

    @classmethod
    def parse_extinf(cls, value: str) -> ExtInf:
        match = cls._extinf_re.match(value)
        if match is None:
            return ExtInf(0, None)

        return ExtInf(
            duration=float(match.group("duration")),
            title=match.group("title"),
        )

    @staticmethod
    def parse_hex(value: str | None) -> bytes | None:
        if value is None:
            return None

        if value[:2] in ("0x", "0X"):
            try:
                return unhexlify(f"{'0' * (len(value) % 2)}{value[2:]}")
            except BinasciiError:
                pass

        log.warning("Discarded invalid hexadecimal-sequence attribute value")
        return None

    @staticmethod
    def parse_iso8601(value: str | None) -> datetime | None:
        try:
            return None if value is None else parse_datetime(value)
        except (ISO8601Error, ValueError):
            log.warning("Discarded invalid ISO8601 attribute value")
            return None

    @staticmethod
    def parse_timedelta(value: str | None) -> timedelta | None:
        return None if value is None else timedelta(seconds=float(value))

    @classmethod
    def parse_resolution(cls, value: str) -> Resolution:
        match = cls._res_re.match(value)
        if match is None:
            return Resolution(width=0, height=0)

        return Resolution(
            width=int(match.group(1)),
            height=int(match.group(2)),
        )

    # ----

    # 4.3.1: Basic Tags

    @parse_tag("EXT-X-VERSION")
    def parse_tag_ext_x_version(self, value: str) -> None:
        """
        EXT-X-VERSION
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.1.2
        """
        self.m3u8.version = int(value)

    # 4.3.2: Media Segment Tags

    @parse_tag("EXTINF")
    def parse_tag_extinf(self, value: str) -> None:
        """
        EXTINF
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.1
        """
        self._expect_segment = True
        self._extinf = self.parse_extinf(value)

    @parse_tag("EXT-X-BYTERANGE")
    def parse_tag_ext_x_byterange(self, value: str) -> None:
        """
        EXT-X-BYTERANGE
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.2
        """
        self._expect_segment = True
        self._byterange = self.parse_byterange(value)

    # noinspection PyUnusedLocal
    @parse_tag("EXT-X-DISCONTINUITY")
    def parse_tag_ext_x_discontinuity(self, value: str) -> None:
        """
        EXT-X-DISCONTINUITY
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.3
        """
        self._discontinuity = True
        self._map = None

    @parse_tag("EXT-X-KEY")
    def parse_tag_ext_x_key(self, value: str) -> None:
        """
        EXT-X-KEY
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.4
        """
        attr = self.parse_attributes(value)
        method = attr.get("METHOD")
        uri = attr.get("URI")

        if not method:
            return

        self._key = Key(
            method=method,
            uri=self.uri(uri) if uri else None,
            iv=self.parse_hex(attr.get("IV")),
            key_format=attr.get("KEYFORMAT"),
            key_format_versions=attr.get("KEYFORMATVERSIONS"),
        )

    @parse_tag("EXT-X-MAP")
    def parse_tag_ext_x_map(self, value: str) -> None:  # version >= 5
        """
        EXT-X-MAP
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.5
        """
        attr = self.parse_attributes(value)
        uri = attr.get("URI")

        if not uri:
            return

        byterange = self.parse_byterange(attr.get("BYTERANGE", ""))
        self._map = Map(
            uri=self.uri(uri),
            key=self._key,
            byterange=byterange,
        )

    @parse_tag("EXT-X-PROGRAM-DATE-TIME")
    def parse_tag_ext_x_program_date_time(self, value: str) -> None:
        """
        EXT-X-PROGRAM-DATE-TIME
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.6
        """
        self._date = self.parse_iso8601(value)

    @parse_tag("EXT-X-DATERANGE")
    def parse_tag_ext_x_daterange(self, value: str) -> None:
        """
        EXT-X-DATERANGE
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.7
        """
        attr = self.parse_attributes(value)
        daterange = DateRange(
            id=attr.pop("ID", None),
            classname=attr.pop("CLASS", None),
            start_date=self.parse_iso8601(attr.pop("START-DATE", None)),
            end_date=self.parse_iso8601(attr.pop("END-DATE", None)),
            duration=self.parse_timedelta(attr.pop("DURATION", None)),
            planned_duration=self.parse_timedelta(attr.pop("PLANNED-DURATION", None)),
            end_on_next=self.parse_bool(attr.pop("END-ON-NEXT", "NO")),
            x=attr,
        )
        self.m3u8.dateranges.append(daterange)

    # 4.3.3: Media Playlist Tags

    @parse_tag("EXT-X-TARGETDURATION")
    def parse_tag_ext_x_targetduration(self, value: str) -> None:
        """
        EXT-X-TARGETDURATION
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.1
        """
        self.m3u8.targetduration = float(value)

    @parse_tag("EXT-X-MEDIA-SEQUENCE")
    def parse_tag_ext_x_media_sequence(self, value: str) -> None:
        """
        EXT-X-MEDIA-SEQUENCE
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.2
        """
        self.m3u8.media_sequence = int(value)

    @parse_tag("EXT-X-DISCONTINUTY-SEQUENCE")
    def parse_tag_ext_x_discontinuity_sequence(self, value: str) -> None:
        """
        EXT-X-DISCONTINUITY-SEQUENCE
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.3
        """
        self.m3u8.discontinuity_sequence = int(value)

    # noinspection PyUnusedLocal
    @parse_tag("EXT-X-ENDLIST")
    def parse_tag_ext_x_endlist(self, value: str) -> None:
        """
        EXT-X-ENDLIST
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.4
        """
        self.m3u8.is_endlist = True

    @parse_tag("EXT-X-PLAYLIST-TYPE")
    def parse_tag_ext_x_playlist_type(self, value: str) -> None:
        """
        EXT-X-PLAYLISTTYPE
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.5
        """
        self.m3u8.playlist_type = value

    # noinspection PyUnusedLocal
    @parse_tag("EXT-X-I-FRAMES-ONLY")
    def parse_tag_ext_x_i_frames_only(self, value: str) -> None:  # version >= 4
        """
        EXT-X-I-FRAMES-ONLY
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.3.6
        """
        self.m3u8.iframes_only = True

    # 4.3.4: Master Playlist Tags

    @parse_tag("EXT-X-MEDIA")
    def parse_tag_ext_x_media(self, value: str) -> None:
        """
        EXT-X-MEDIA
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.4.1
        """
        attr = self.parse_attributes(value)
        mediatype = attr.get("TYPE")
        uri = attr.get("URI")
        group_id = attr.get("GROUP-ID")
        name = attr.get("NAME")

        if not mediatype or not group_id or not name:
            return

        media = Media(
            type=mediatype,
            uri=self.uri(uri) if uri else None,
            group_id=group_id,
            language=attr.get("LANGUAGE"),
            name=name,
            default=self.parse_bool(attr.get("DEFAULT", "NO")),
            autoselect=self.parse_bool(attr.get("AUTOSELECT", "NO")),
            forced=self.parse_bool(attr.get("FORCED", "NO")),
            characteristics=attr.get("CHARACTERISTICS"),
        )
        self.m3u8.media.append(media)

    @parse_tag("EXT-X-STREAM-INF")
    def parse_tag_ext_x_stream_inf(self, value: str) -> None:
        """
        EXT-X-STREAM-INF
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.4.2
        """
        self._expect_playlist = True
        self._streaminf = self.parse_attributes(value)

    @parse_tag("EXT-X-I-FRAME-STREAM-INF")
    def parse_tag_ext_x_i_frame_stream_inf(self, value: str) -> None:
        """
        EXT-X-I-FRAME-STREAM-INF
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.4.3
        """
        attr = self.parse_attributes(value)
        uri = attr.get("URI")

        streaminf = self._streaminf or attr
        self._streaminf = None

        if not uri:
            return

        stream_info = self.create_stream_info(streaminf, IFrameStreamInfo)
        playlist = HLSPlaylist(
            uri=self.uri(uri),
            stream_info=stream_info,
            media=[],
            is_iframe=True,
        )
        self.m3u8.playlists.append(playlist)

    @parse_tag("EXT-X-SESSION-DATA")
    def parse_tag_ext_x_session_data(self, value: str) -> None:
        """
        EXT-X-SESSION-DATA
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.4.4
        """

    @parse_tag("EXT-X-SESSION-KEY")
    def parse_tag_ext_x_session_key(self, value: str) -> None:
        """
        EXT-X-SESSION-KEY
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.4.5
        """

    # 4.3.5: Media or Master Playlist Tags

    @parse_tag("EXT-X-INDEPENDENT-SEGMENTS")
    def parse_tag_ext_x_independent_segments(self, value: str) -> None:
        """
        EXT-X-INDEPENDENT-SEGMENTS
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.5.1
        """

    @parse_tag("EXT-X-START")
    def parse_tag_ext_x_start(self, value: str) -> None:
        """
        EXT-X-START
        https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.5.2
        """
        attr = self.parse_attributes(value)
        self.m3u8.start = Start(
            time_offset=float(attr.get("TIME-OFFSET", 0)),
            precise=self.parse_bool(attr.get("PRECISE", "NO")),
        )

    # Removed tags
    # https://datatracker.ietf.org/doc/html/rfc8216#section-7

    @parse_tag("EXT-X-ALLOW-CACHE")
    def parse_tag_ext_x_allow_cache(self, value: str) -> None:  # version < 7
        self.m3u8.allow_cache = self.parse_bool(value)

    # ----

    def parse_line(self, line: str) -> None:
        if line.startswith("#"):
            tag, value = self.split_tag(line)
            if not tag or value is None or tag not in self._TAGS:
                return
            self._TAGS[tag](self, value)

        elif self._expect_segment:
            self._expect_segment = False
            segment = self.get_segment(self.uri(line))
            self.m3u8.segments.append(segment)

        elif self._expect_playlist:
            self._expect_playlist = False
            playlist = self.get_playlist(self.uri(line))
            self.m3u8.playlists.append(playlist)

    def parse(self, data: str | Response) -> TM3U8_co:
        lines: Iterator[str]
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
                log.warning(f"Malformed HLS Playlist. Expected #EXTM3U, but got {line[:250]}")
                raise ValueError("Missing #EXTM3U header")

        lines = log.iter(ALL, lines)

        parse_line = self.parse_line
        for line in lines:
            parse_line(line)

        # Associate Media entries with each Playlist
        for playlist in self.m3u8.playlists:
            for media_type in ("audio", "video", "subtitles"):
                group_id = getattr(playlist.stream_info, media_type, None)
                if group_id:
                    for media in filter(lambda m: m.group_id == group_id, self.m3u8.media):
                        playlist.media.append(media)

        self.m3u8.is_master = not not self.m3u8.playlists

        # Update segment numbers
        media_sequence = self.m3u8.media_sequence or 0
        for i, segment in enumerate(self.m3u8.segments):
            segment.num = media_sequence + i

        return self.m3u8

    def uri(self, uri: str) -> str:
        if uri and urlparse(uri).scheme:
            return uri
        elif uri and self.m3u8.uri:
            return urljoin(self.m3u8.uri, uri)
        else:
            return uri

    def get_segment(self, uri: str, **data) -> HLSSegment:
        extinf: ExtInf = self._extinf or ExtInf(0, None)
        self._extinf = None

        discontinuity = self._discontinuity
        self._discontinuity = False

        byterange = self._byterange
        self._byterange = None

        date = self._date
        self._date = None

        # noinspection PyArgumentList
        return self.__segment__(
            uri=uri,
            num=-1,
            duration=extinf.duration,
            title=extinf.title,
            key=self._key,
            discontinuity=discontinuity,
            byterange=byterange,
            date=date,
            map=self._map,
            **data,
        )

    def get_playlist(self, uri: str, **data) -> HLSPlaylist:
        streaminf = self._streaminf or {}
        self._streaminf = None

        stream_info = self.create_stream_info(streaminf)

        # noinspection PyArgumentList
        return self.__playlist__(
            uri=uri,
            stream_info=stream_info,
            media=[],
            is_iframe=False,
            **data,
        )


def parse_m3u8(
    data: str | Response,
    base_uri: str | None = None,
    parser: type[M3U8Parser[TM3U8_co, THLSSegment_co, THLSPlaylist_co]] = M3U8Parser,
) -> TM3U8_co:
    """
    Parse an M3U8 playlist from a string of data or an HTTP response.

    If specified, *base_uri* is the base URI that relative URIs will
    be joined together with, otherwise relative URIs will be as is.

    If specified, *parser* can be an M3U8Parser subclass to be used
    to parse the data.
    """
    if base_uri is None and isinstance(data, Response):
        base_uri = data.url

    return parser(base_uri).parse(data)
