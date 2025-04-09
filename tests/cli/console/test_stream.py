from __future__ import annotations

from io import BytesIO, TextIOWrapper
from os import linesep
from typing import TYPE_CHECKING

import pytest

from streamlink_cli.console.stream import (
    ConsoleOutputStream,
    ConsoleOutputStreamANSI,
    ConsoleStatusMessage,
)


if TYPE_CHECKING:
    from typing_extensions import Buffer


nl = linesep.encode("ascii")


@pytest.fixture()
def buffer():
    return BytesIO()


@pytest.fixture()
def stream(buffer: BytesIO):
    # stdout/stderr is line buffered, which implies flushes when writing \n or \r
    return TextIOWrapper(buffer, encoding="utf-8", line_buffering=True)


@pytest.fixture()
def console_output_stream(stream: TextIOWrapper):
    return ConsoleOutputStream(stream)


class TestConsoleOutputStreamFeatureDetection:
    @pytest.fixture()
    def stream(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, stream: TextIOWrapper):
        isatty = getattr(request, "param", True)
        setattr(stream, "isatty", lambda: isatty)  # noqa: B010

        return stream

    # noinspection PyTestParametrized
    @pytest.mark.parametrize(
        ("stream", "os_environ", "expected"),
        [
            pytest.param(False, {}, ConsoleOutputStream, id="posix-notatty"),
            pytest.param(True, {}, ConsoleOutputStreamANSI, id="posix-isatty"),
            pytest.param(True, {"TERM": "dumb"}, ConsoleOutputStream, id="posix-TERM=dumb"),
            pytest.param(True, {"TERM": "unknown"}, ConsoleOutputStream, id="posix-TERM=unknown"),
        ],
        indirect=["os_environ", "stream"],
    )
    def test_class_type(self, os_environ: dict, console_output_stream: ConsoleOutputStream, expected: ConsoleOutputStream):
        assert type(console_output_stream) is expected


class TestConsoleOutputStream:
    @pytest.fixture(autouse=True)
    def _mock_new(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(ConsoleOutputStream, "__new__", lambda *_, **__: object.__new__(ConsoleOutputStream))

    def test_supports_status_messages(self, console_output_stream: ConsoleOutputStream):
        assert not console_output_stream.supports_status_messages()

    def test_write(self, buffer: BytesIO, console_output_stream: ConsoleOutputStream):
        assert buffer.getvalue() == b""

        assert console_output_stream.write("foo") == 0
        assert buffer.getvalue() == b""
        assert console_output_stream._line_buffer == ["foo"]

        assert console_output_stream.write("bar") == 0
        assert buffer.getvalue() == b""
        assert console_output_stream._line_buffer == ["foo", "bar"]

        assert console_output_stream.write("baz\n123\n456\n") == (6 + 4) + 4 + 4
        assert buffer.getvalue() == b"foobarbaz" + nl + b"123" + nl + b"456" + nl
        assert console_output_stream._line_buffer == []

        assert console_output_stream.write("abc") == 0
        console_output_stream.flush()
        assert buffer.getvalue() == b"foobarbaz" + nl + b"123" + nl + b"456" + nl + b"abc"
        assert console_output_stream._line_buffer == []

        console_output_stream.writelines(["QWERTY\n", "ASDF"])
        assert buffer.getvalue() == b"foobarbaz" + nl + b"123" + nl + b"456" + nl + b"abcQWERTY" + nl
        assert console_output_stream._line_buffer == ["ASDF"]
        console_output_stream.flush()
        assert buffer.getvalue() == b"foobarbaz" + nl + b"123" + nl + b"456" + nl + b"abcQWERTY" + nl + b"ASDF"

    def test_write_status_message(self, buffer: BytesIO, console_output_stream: ConsoleOutputStream):
        assert console_output_stream.write(ConsoleStatusMessage("foo")) == 0
        assert console_output_stream._line_buffer == []
        console_output_stream.flush()
        assert buffer.getvalue() == b""

    def test_close(self, buffer: BytesIO, console_output_stream: ConsoleOutputStream):
        def fakewrite(s: Buffer) -> int:
            msg = bytes(s)
            fakebuffer.append(msg)

            return len(msg)

        fakebuffer: list[Buffer] = []
        buffer.write = fakewrite  # type: ignore[method-assign]

        assert console_output_stream.write("foo") == 0
        assert fakebuffer == []
        assert console_output_stream._line_buffer == ["foo"]
        assert not console_output_stream.closed

        console_output_stream.close()
        assert fakebuffer == [b"foo"]
        assert console_output_stream._line_buffer == []
        assert console_output_stream.closed

        console_output_stream.close()  # noop - does not raise

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.write("foo")

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.writelines(["foo", "bar"])

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.flush()


class TestConsoleOutputStreamANSI:
    @pytest.fixture(autouse=True)
    def _mock_new(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(ConsoleOutputStream, "__new__", lambda *_, **__: object.__new__(ConsoleOutputStreamANSI))

    @pytest.fixture()
    def fakebuffer(self, buffer: BytesIO):
        def fakewrite(s: Buffer) -> int:
            msg = bytes(s)
            fakebuffer.append(msg)

            return len(msg)

        fakebuffer: list[Buffer] = []
        buffer.write = fakewrite  # type: ignore[method-assign]

        return fakebuffer

    def test_supports_status_messages(self, console_output_stream: ConsoleOutputStreamANSI):
        assert console_output_stream.supports_status_messages()

    def test_write(self, buffer: BytesIO, console_output_stream: ConsoleOutputStreamANSI):
        clr_eol = console_output_stream._CR_CLREOL.encode("ascii")
        len_clr_eol = len(clr_eol)
        assert len_clr_eol == 4

        assert console_output_stream.write("foo") == 0
        assert buffer.getvalue() == b""
        assert console_output_stream._line_buffer == ["foo"]
        assert console_output_stream._last_status == ""

        assert console_output_stream.write("bar\n") == 3 + 4
        assert buffer.getvalue() == b"foobar" + nl
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""

        assert console_output_stream.write(ConsoleStatusMessage("123\n")) == 3
        assert buffer.getvalue() == b"foobar" + nl + b"123"
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == "123"

        assert console_output_stream.write(ConsoleStatusMessage("456\n")) == len_clr_eol + 3
        assert buffer.getvalue() == b"foobar" + nl + b"123" + clr_eol + b"456"
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == "456"

        assert console_output_stream.write("abc") == 0
        assert buffer.getvalue() == b"foobar" + nl + b"123" + clr_eol + b"456"
        assert console_output_stream._line_buffer == ["abc"]
        assert console_output_stream._last_status == "456"

        assert console_output_stream.write(ConsoleStatusMessage("789\n")) == len_clr_eol + 3
        assert buffer.getvalue() == b"foobar" + nl + b"123" + clr_eol + b"456" + clr_eol + b"789"
        assert console_output_stream._line_buffer == ["abc"]
        assert console_output_stream._last_status == "789"

        assert console_output_stream.write("def\n") == 3 + 4 + len_clr_eol + len(console_output_stream._last_status)
        assert buffer.getvalue() == (
            b"foobar" + nl + b"123" + clr_eol + b"456" + clr_eol + b"789" + clr_eol + b"abcdef" + nl + b"789"
        )
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == "789"

    def test_close(self, console_output_stream: ConsoleOutputStreamANSI):
        console_output_stream.close()

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.write("foo")

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.writelines(["foo", "bar"])

        with pytest.raises(ValueError, match=r"^I/O operation on closed file\.$"):
            console_output_stream.flush()

    def test_close_without_line_buffer_without_status(
        self,
        fakebuffer: list[bytes],
        console_output_stream: ConsoleOutputStreamANSI,
    ):
        assert console_output_stream.write("foo\n") == 4
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        console_output_stream.close()
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert console_output_stream.closed

        console_output_stream.close()  # noop - does not raise

    def test_close_with_line_buffer_without_status(
        self,
        fakebuffer: list[bytes],
        console_output_stream: ConsoleOutputStreamANSI,
    ):
        assert console_output_stream.write("foo\n") == 4
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        assert console_output_stream.write("bar") == 0
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == ["bar"]
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        console_output_stream.close()
        assert fakebuffer == [b"foo" + nl, b"bar" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert console_output_stream.closed

        console_output_stream.close()  # noop - does not raise

    def test_close_without_line_buffer_with_status(
        self,
        fakebuffer: list[bytes],
        console_output_stream: ConsoleOutputStreamANSI,
    ):
        assert console_output_stream.write("foo\n") == 4
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        assert console_output_stream.write(ConsoleStatusMessage("123\n")) == 3
        assert fakebuffer == [b"foo" + nl, b"123"]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == "123"
        assert not console_output_stream.closed

        console_output_stream.close()
        assert fakebuffer == [b"foo" + nl, b"123", nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert console_output_stream.closed

        console_output_stream.close()  # noop - does not raise

    def test_close_with_line_buffer_with_status(
        self,
        fakebuffer: list[bytes],
        console_output_stream: ConsoleOutputStreamANSI,
    ):
        clr_eol = console_output_stream._CR_CLREOL.encode("ascii")

        assert console_output_stream.write("foo\n") == 4
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        assert console_output_stream.write("bar") == 0
        assert fakebuffer == [b"foo" + nl]
        assert console_output_stream._line_buffer == ["bar"]
        assert console_output_stream._last_status == ""
        assert not console_output_stream.closed

        assert console_output_stream.write(ConsoleStatusMessage("123\n")) == 3
        assert fakebuffer == [b"foo" + nl, b"123"]
        assert console_output_stream._line_buffer == ["bar"]
        assert console_output_stream._last_status == "123"
        assert not console_output_stream.closed

        console_output_stream.close()
        assert fakebuffer == [b"foo" + nl, b"123", clr_eol + b"bar" + nl + b"123" + nl]
        assert console_output_stream._line_buffer == []
        assert console_output_stream._last_status == ""
        assert console_output_stream.closed

        console_output_stream.close()  # noop - does not raise
