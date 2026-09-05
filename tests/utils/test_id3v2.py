from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from streamlink.utils.id3v2 import (
    ID3v2,
    ID3v2Error,
    ID3v2Frame,
    ID3v2FrameError,
    ID3v2NoID3v2Error,
    ID3v2NotEnoughDataError,
    parse_frame,
    parse_frame_priv,
)


if TYPE_CHECKING:
    from collections.abc import Sequence


def ss_int(value: int) -> bytes:
    return bytes([
        (value >> 21) & 0x7F,
        (value >> 14) & 0x7F,
        (value >> 7) & 0x7F,
        value & 0x7F,
    ])


class TestID3v2SyncsafeInteger:
    def test_valid(self):
        assert ID3v2._parse_syncsafe_integer(b"\x00\x00\x00\x00") == 0
        assert ID3v2._parse_syncsafe_integer(b"\x00\x00\x00\x7f") == 0x7F
        assert ID3v2._parse_syncsafe_integer(b"\x00\x00\x01\x00") == 0x80
        assert ID3v2._parse_syncsafe_integer(b"\x00\x02\x00\x00") == 0x8000
        assert ID3v2._parse_syncsafe_integer(b"\x7f\x7f\x7f\x7f") == 0xFFFFFFF

    @pytest.mark.parametrize("pos", range(4))
    def test_invalid(self, pos: int):
        with pytest.raises(ID3v2Error, match="Invalid ID3v2 size value"):
            ID3v2._parse_syncsafe_integer(pos * b"\x00" + b"\x80" + (3 - pos) * b"\x00")


class TestNoID3v2:
    @pytest.mark.parametrize("data", [(b"",), (b"foo",), (b"foo", b"bar")])
    def test_insufficient(self, data: Sequence[bytes]):
        iterator = iter(data)
        parser = ID3v2(iterator)
        with pytest.raises(ID3v2NotEnoughDataError, match=r"Not enough data for header"):
            parser.parse()
        assert parser.bytes_read == 0
        assert not parser.parsed
        assert b"".join(parser) == b"".join(data)
        assert next(iterator, None) is None

    def test_invalid(self):
        parser = ID3v2(iter((b"not ID3v2!",)))
        with pytest.raises(ID3v2NoID3v2Error):
            parser.parse()
        assert parser.bytes_read == 0
        assert not parser.parsed
        assert b"".join(parser) == b"not ID3v2!"


class TestID3v2Header:
    def test_valid_no_frames(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00\x00\x00\x00\x00remaining"]))
        parser.parse()
        assert parser.bytes_read == 0

        header = parser.header
        assert header.major == 4
        assert header.revision == 0
        assert not header.extended
        assert not header.unsynchronization
        assert not header.experimental
        assert not header.footer
        assert header.size == 0

        assert b"".join(parser) == b"remaining"

    @pytest.mark.parametrize(
        ("data", "error_msg"),
        [
            pytest.param(b"ID3\x03\x00\x00\x00\x00\x00\x00", "Incompatible ID3v2 version"),
            pytest.param(b"ID3\x04\x00\x01\x00\x00\x00\x00", "Invalid ID3v2 flags"),
        ],
    )
    def test_invalid(self, data: bytes, error_msg: str):
        parser = ID3v2(iter([data]))
        with pytest.raises(ID3v2Error, match=error_msg):
            parser.parse()
        assert parser.bytes_read == 0
        assert b"".join(parser) == data


class TestID3v2ExtendedHeader:
    def test_discards(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x40", ss_int(24), ss_int(20), 20 * b"\x00", b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 24
        assert parser.header.extended
        assert b"".join(parser) == b"remaining"

    def test_not_enough_data(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x40", ss_int(10), 3 * b"\x00"]))
        with pytest.raises(ID3v2Error, match=r"Not enough data for extended header"):
            parser.parse()
        assert parser.bytes_read == 3
        assert b"".join(parser) == b""

    def test_insufficient(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x40", ss_int(10), ss_int(10), 5 * b"\x00"]))
        with pytest.raises(ID3v2Error, match=r"Could not read 6 bytes of ID3v2 extended header"):
            parser.parse()
        assert parser.bytes_read == 9
        assert b"".join(parser) == b""

    def test_invalid_header_size(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x40", ss_int(10), ss_int(5), 6 * b"\x00"]))
        with pytest.raises(ID3v2Error, match=r"Invalid extended header size: 5"):
            parser.parse()
        assert parser.bytes_read == 4
        assert b"".join(parser) == 6 * b"\x00"


class TestID3v2Footer:
    def test_discards(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x10", ss_int(10), 10 * b"\x00", b"3DI\x04\x00\x10", ss_int(10), b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 20
        assert parser.header.footer
        assert b"".join(parser) == b"remaining"

    def test_mismatch(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x10", ss_int(10), 10 * b"\x00", b"3DI\x04\x00\x00", ss_int(10), b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 10
        assert parser.header.footer
        assert b"".join(parser) == b"".join([b"3DI\x04\x00\x00", ss_int(10), b"remaining"])

    def test_insufficient(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x10", ss_int(10), 10 * b"\x00", b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 10
        assert parser.header.footer
        assert b"".join(parser) == b"remaining"


class TestID3v2Frames:
    def test_not_enough_header_data(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(9), 9 * b"\x00", b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 9
        assert not parser.frames
        assert b"".join(parser) == b"remaining"

    def test_not_a_frame(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(10), 4 * b"\x00", 6 * b"\x01", b"remaining"]))
        parser.parse()
        assert parser.bytes_read == 10
        assert not parser.frames
        assert b"".join(parser) == b"remaining"

    def test_check_boundary_on_read(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(10), b"PRIV", ss_int(100), b"\x00\x00remaining"]))
        with pytest.raises(ID3v2Error, match=r"Attempting to read more ID3v2 than allowed"):
            parser.parse()
        assert parser.bytes_read == 10
        assert not parser.frames
        assert b"".join(parser) == b"remaining"

    def test_not_enough_frame_data(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(20), b"PRIV", ss_int(10), b"\x00\x00", 9 * b"\x00"]))
        with pytest.raises(ID3v2Error, match=r"Not enough data for frame data"):
            parser.parse()
        assert parser.bytes_read == 19
        assert b"".join(parser) == b""

    def test_not_enough_frame_data_with_offsets(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(11), b"PRIV", ss_int(1), b"\x00\x40\x00"]))
        with pytest.raises(ID3v2Error, match=r"Not enough data for frame data"):
            parser.parse()
        assert parser.bytes_read == 11
        assert b"".join(parser) == b""

    def test_offsets(self):
        parser = ID3v2(
            iter([
                b"ID3\x04\x00\x00",
                ss_int(21),
                b"PRIV",
                ss_int(11),
                # grouping identity | compression | encryption | data length indicator
                b"\x00\x4d",
                b"\xf0\xf1\xf2\xf3\xf4\xf5",
                b"\x01\x23\x00\x45\x67",
                b"remaining",
            ]),
        )
        parser.parse()
        assert parser.bytes_read == 21
        assert parser.frames == [
            ID3v2Frame(
                ident=b"PRIV",
                size=11,
                data=bytearray(b"\x01\x23\x00\x45\x67"),
                result=None,
                error=None,
                grouping_identity=True,
                compression=True,
                encryption=True,
                unsynchronization=False,
                data_length_indicator=True,
            ),
        ]
        assert b"".join(parser) == b"remaining"

    def test_frame_error(self):
        parser = ID3v2(
            iter([
                b"ID3\x04\x00\x00",
                ss_int(14),
                b"PRIV",
                ss_int(4),
                b"\x00\x00",
                b"\x01\x23\x45\x67",
                b"remaining",
            ]),
        )
        parser.parse()
        assert parser.bytes_read == 14
        assert parser.frames == [
            ID3v2Frame(
                ident=b"PRIV",
                size=4,
                data=bytearray(b"\x01\x23\x45\x67"),
                result=None,
                error=ID3v2FrameError("Invalid PRIV frame data"),
                grouping_identity=False,
                compression=False,
                encryption=False,
                unsynchronization=False,
                data_length_indicator=False,
            ),
        ]
        assert b"".join(parser) == b"remaining"


class TestID3v2FrameCallbacks:
    @dataclass
    class Result:
        my_result_value: bool

    @pytest.mark.parametrize(
        ("value", "resultclass", "expected"),
        [
            (b"abcd", None, True),
            (b"wxyz", None, False),
            (b"abcd", Result, Result(True)),
            (b"wxyz", Result, Result(False)),
        ],
    )
    def test_frame(self, value: bytes, resultclass: type | None, expected: bool | Result):
        class CustomID3v2(ID3v2):
            @parse_frame(b"ABCD", resultclass)
            def _parse_frame_asdf(self, ident: bytes, data: bytearray):
                return data.decode("ascii") == ident.decode("ascii").lower()

        assert ID3v2._FRAME_PARSERS.get(b"ABCD") is None
        assert ID3v2._FRAME_PARSERS_PRIV.get(b"ABCD") is None
        assert CustomID3v2._FRAME_PARSERS.get(b"ABCD") is not None
        assert CustomID3v2._FRAME_PARSERS_PRIV.get(b"ABCD") is None

        parser = CustomID3v2(iter([b"ID3\x04\x00\x00", ss_int(14), b"ABCD", ss_int(4), b"\x00\x00", value]))
        parser.parse()
        assert parser.bytes_read == 14
        assert parser.frames == [
            ID3v2Frame(
                ident=b"ABCD",
                size=4,
                data=bytearray(value),
                result=expected,
                error=None,
                grouping_identity=False,
                compression=False,
                encryption=False,
                unsynchronization=False,
                data_length_indicator=False,
            ),
        ]

    @pytest.mark.parametrize(
        ("value", "resultclass", "expected"),
        [
            (b"ABCD", None, True),
            (b"WXYZ", None, False),
            (b"ABCD", Result, Result(True)),
            (b"WXYZ", Result, Result(False)),
        ],
    )
    def test_priv_frame(self, value: bytes, resultclass: type | None, expected: bool | Result):
        class CustomID3v2(ID3v2):
            @parse_frame_priv(b"abcd", resultclass)
            def _parse_frame_asdf(self, ident: bytes, data: bytearray):
                return data.decode("ascii") == ident.decode("ascii").upper()

        assert ID3v2._FRAME_PARSERS.get(b"abcd") is None
        assert ID3v2._FRAME_PARSERS_PRIV.get(b"abcd") is None
        assert CustomID3v2._FRAME_PARSERS.get(b"abcd") is None
        assert CustomID3v2._FRAME_PARSERS_PRIV.get(b"abcd") is not None

        parser = CustomID3v2(iter([b"ID3\x04\x00\x00", ss_int(19), b"PRIV", ss_int(9), b"\x00\x00abcd\x00", value]))
        parser.parse()
        assert parser.bytes_read == 19
        assert parser.frames == [
            ID3v2Frame(
                ident=b"PRIV",
                size=9,
                data=bytearray(b"abcd\x00" + value),
                result=expected,
                error=None,
                grouping_identity=False,
                compression=False,
                encryption=False,
                unsynchronization=False,
                data_length_indicator=False,
            ),
        ]


class TestID3v2Parse:
    def test_parse_tags(self):
        tags, iterator = ID3v2.parse_tags(iter([b"ID3\x04\x00\x00", ss_int(0), b"ID3\x04\x00\x00", ss_int(0), b"remaining"]))
        assert len(tags) == 2
        assert b"".join(iterator) == b"remaining"
        assert all(tag.parsed for tag in tags)
        assert all(not tag.frames for tag in tags)

    def test_parse_twice(self):
        parser = ID3v2(iter([b"ID3\x04\x00\x00", ss_int(0), b"remaining"]))
        assert not parser.parsed
        parser.parse()
        assert parser.parsed
        assert parser.bytes_read == 0
        parser.parse()
        assert parser.bytes_read == 0
        assert b"".join(parser) == b"remaining"
