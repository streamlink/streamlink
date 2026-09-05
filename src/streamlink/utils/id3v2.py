from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from struct import unpack
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from typing_extensions import Self

    TFrameParser: TypeAlias = "Callable[[ID3v2, bytes, bytearray], Any]"


class ID3v2Error(Exception):
    def __hash__(self) -> int:  # pragma: no cover
        return hash((type(self), self.args))

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self) or not isinstance(other, Exception):  # pragma: no cover
            return NotImplemented
        return self.args == other.args


class ID3v2NotEnoughDataError(ID3v2Error):
    pass


class ID3v2NoID3v2Error(ID3v2Error):
    pass


class ID3v2FrameError(ID3v2Error):
    pass


@dataclass(kw_only=True)
class ID3v2Header:
    major: int
    revision: int
    unsynchronization: bool
    extended: bool
    experimental: bool
    footer: bool
    size: int
    data: bytearray


@dataclass(kw_only=True)
class ID3v2Frame:
    ident: bytes
    size: int
    data: bytearray
    result: Any
    error: ID3v2FrameError | None

    # frame status flags
    # tag_alter_preservation: bool = False
    # file_alter_preservation: bool = False
    # read_only: bool = False

    # frame format flags
    grouping_identity: bool = False
    compression: bool = False
    encryption: bool = False
    unsynchronization: bool = False
    data_length_indicator: bool = False


_SYMBOL_FRAME_PARSER = "__PARSE_ID3v2_FRAME"
_FRAME_PARSERS = "_FRAME_PARSERS"
_FRAME_PARSERS_PRIV = "_FRAME_PARSERS_PRIV"


def _parse_frame_factory(frame_type: str):
    def _decorator(frame_name: bytes, frame_result_class: type | None = None):
        def decorator(func: TFrameParser) -> TFrameParser:
            setattr(func, _SYMBOL_FRAME_PARSER, (frame_type, frame_name, frame_result_class))
            return func

        return decorator

    return _decorator


parse_frame = _parse_frame_factory(_FRAME_PARSERS)
parse_frame_priv = _parse_frame_factory(_FRAME_PARSERS_PRIV)


class _ID3v2Meta(type):
    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)

        frame_types = {_FRAME_PARSERS, _FRAME_PARSERS_PRIV}
        for frame_type in frame_types:
            setattr(cls, frame_type, dict(getattr(cls, frame_type, {})))
        for member in namespace.values():
            frame_type, frame_name, frame_result_class = getattr(member, _SYMBOL_FRAME_PARSER, (None, None, None))
            if frame_type not in frame_types or type(frame_name) is not bytes:
                continue
            getattr(cls, frame_type)[frame_name] = member, frame_result_class


class ID3v2(metaclass=_ID3v2Meta):
    """
    A very basic ID3v2.4.0 parser.
    The main goal of this parser is to be able to parse ID3v2 tags in HLS packed audio streams.

    Not all ID3v2 features are therefore implemented, like support for
    unsynch bytes, extended headers, frame group idents, frame compression or frame encryption.
    """

    MAGICBYTES_HEADER = b"ID3"
    MAGICBYTES_FOOTER = b"3DI"
    SUPPORTED_VERSION = 4, 0

    _FRAME_PARSERS: ClassVar[Mapping[bytes, tuple[TFrameParser, type | None]]]
    _FRAME_PARSERS_PRIV: ClassVar[Mapping[bytes, tuple[TFrameParser, type | None]]]

    def __init__(self, iterator: Iterator[bytes]):
        self._bytes_read = 0
        self._iterator = iterator
        self.parsed = False
        self.header: ID3v2Header = None  # type: ignore[assignment, ty:invalid-assignment]
        self.frames: list[ID3v2Frame] = []

    @classmethod
    def parse_tags(cls, iterator: Iterator[bytes]) -> tuple[list[Self], Iterator[bytes]]:
        tags = []
        while True:
            parser = cls(iterator)
            try:
                parser.parse()
            except (ID3v2NoID3v2Error, ID3v2NotEnoughDataError):
                break
            finally:
                iterator = iter(parser)
            tags.append(parser)

        return tags, iterator

    @property
    def bytes_read(self):
        return self._bytes_read

    def parse(self) -> None:
        if self.parsed:
            return

        self.header = self._parse_header()
        self._parse_extended_header()
        self.frames.extend(self._parse_frames())

        self._consume_padding()
        self._parse_footer()

        self.parsed = True

    def __iter__(self):
        yield from self._iterator

    def _prepend_iterator(self, data: bytes | bytearray):
        if data:
            self._iterator = chain((bytes(data),), self._iterator)

    def _read(self, size: int, *, check_boundary: bool = True, increment_counter: bool = True) -> bytearray:
        if check_boundary and self._bytes_read + size > self.header.size:
            raise ID3v2Error("Attempting to read more ID3v2 than allowed")

        buffer = bytearray()
        needed = size

        for chunk in self._iterator:
            if not chunk:
                continue

            chunk_len = len(chunk)
            if chunk_len < needed:
                buffer.extend(chunk)
                needed -= chunk_len
            else:
                buffer.extend(chunk[:needed])
                leftover = chunk[needed:]
                if leftover:
                    self._prepend_iterator(leftover)
                break

        if increment_counter:
            self._bytes_read += len(buffer)

        return buffer

    def _parse_header(self) -> ID3v2Header:
        data = self._read(10, check_boundary=False, increment_counter=False)
        if len(data) < 10:
            # add data back to the iterator if not enough data could be read
            self._prepend_iterator(data)
            raise ID3v2NotEnoughDataError("Not enough data for header")

        ident, major, revision, flags, size_bytes = unpack(">3sBBB4s", data)

        try:  # ruff: ignore[too-many-statements-in-try-clause]
            if ident != self.MAGICBYTES_HEADER:
                raise ID3v2NoID3v2Error
            if (major, revision) != self.SUPPORTED_VERSION:
                raise ID3v2Error("Incompatible ID3v2 version")
            if flags & 0x0F:
                raise ID3v2Error("Invalid ID3v2 flags")

            unsynchronization = bool(flags & 0x80)
            extended = bool(flags & 0x40)
            experimental = bool(flags & 0x20)
            footer = bool(flags & 0x10)
            size = self._parse_syncsafe_integer(size_bytes)

        except:
            # add data back to the iterator if parsing the header fails
            self._prepend_iterator(data)
            raise

        return ID3v2Header(
            major=major,
            revision=revision,
            unsynchronization=unsynchronization,
            extended=extended,
            experimental=experimental,
            footer=footer,
            size=size,
            data=data,
        )

    def _parse_extended_header(self):
        if not self.header.extended:
            return

        data = self._read(4)
        if len(data) < 4:
            raise ID3v2Error("Not enough data for extended header")

        size = self._parse_syncsafe_integer(data)
        if size < 6:
            raise ID3v2Error(f"Invalid extended header size: {size}")

        size -= 4

        # discard extended header bytes
        if len(self._read(size)) < size:
            raise ID3v2Error(f"Could not read {size} bytes of ID3v2 extended header")

    def _parse_frames(self) -> Iterator[ID3v2Frame]:
        while self._bytes_read + 10 <= self.header.size:
            if (frame := self._parse_frame()) is None:
                break
            yield frame

    def _parse_frame(self) -> ID3v2Frame | None:
        header = self._read(10)
        ident, size_bytes, _status_flags, format_flags = unpack(">4s4s2B", header)

        # potential padding bytes at the end of the tag
        if ident == b"\x00\x00\x00\x00":
            return None

        grouping_identity = bool(format_flags & 0x40)
        compression = bool(format_flags & 0x08)
        encryption = bool(format_flags & 0x04)
        data_length_indicator = bool(format_flags & 0x01)

        offset = int(grouping_identity) + int(encryption) + 4 * int(data_length_indicator or compression)

        size = self._parse_syncsafe_integer(size_bytes)
        data = self._read(size)
        if len(data) < size or offset >= len(data):
            raise ID3v2NotEnoughDataError("Not enough data for frame data")

        if offset > 0:
            data = data[offset:]

        result: Any = None
        error: ID3v2FrameError | None = None
        try:
            result = self._get_parser_result(self._FRAME_PARSERS, ident, data)
        except ID3v2FrameError as err:
            error = err

        return ID3v2Frame(
            ident=ident,
            size=size,
            data=data,
            result=result,
            error=error,
            grouping_identity=grouping_identity,
            compression=compression,
            encryption=encryption,
            data_length_indicator=data_length_indicator,
        )

    def _consume_padding(self):
        if (remaining := self.header.size - self._bytes_read) > 0:
            self._read(remaining)

    def _parse_footer(self):
        if not self.header.footer:
            return

        data = self._read(10, check_boundary=False)
        if len(data) == 10:
            ident, major, revision, flags, size_bytes = unpack(">3sBBB4s", data)
            size = self._parse_syncsafe_integer(size_bytes)
            if (
                ident == self.MAGICBYTES_FOOTER
                and (major, revision) == (self.header.major, self.header.revision)
                and flags == self.header.data[5]
                and size == self.header.size
            ):
                return

        self._bytes_read -= len(data)
        self._prepend_iterator(data)

    @staticmethod
    def _parse_syncsafe_integer(data: bytes | bytearray):
        size_a, size_b, size_c, size_d = unpack(">4B", data)
        if size_a & 0x80 or size_b & 0x80 or size_c & 0x80 or size_d & 0x80:
            raise ID3v2Error("Invalid ID3v2 size value")

        return size_a << 21 | size_b << 14 | size_c << 7 | size_d

    def _get_parser_result(self, parsers: Mapping[bytes, tuple[TFrameParser, type | None]], ident: bytes, data: bytearray):
        if not (parser := parsers.get(ident)):
            return None
        callback, frame_result_class = parser
        result = callback(self, ident, data)
        if frame_result_class:
            result = frame_result_class(result)

        return result

    @parse_frame(b"PRIV")
    def _parse_frame_priv(self, _ident: bytes, data: bytearray):
        try:
            owner, data = data.split(b"\0", 1)
        except ValueError:
            raise ID3v2FrameError("Invalid PRIV frame data") from None

        return self._get_parser_result(self._FRAME_PARSERS_PRIV, bytes(owner), data)
