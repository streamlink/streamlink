from io import StringIO

import pytest

from streamlink_cli.utils.terminal import TerminalOutput
from tests import posix_only, windows_only


class TestWidth:
    @pytest.mark.parametrize("chars,expected", [
        ("ABCDEFGHIJ", 10),
        ("A你好世界こんにちは안녕하세요B", 30),
        ("·「」『』【】-=！@#￥%……&×（）", 30),
    ])
    def test_width(self, chars, expected):
        assert TerminalOutput.width(chars) == expected

    @pytest.mark.parametrize("prefix,max_len,expected", [
        ("你好世界こんにちは안녕하세요CD", 10, "녕하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 9, "하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 23, "こんにちは안녕하세요CD"),
    ])
    def test_cut(self, prefix, max_len, expected):
        assert TerminalOutput.cut(prefix, max_len) == expected


class TestOutput:
    @pytest.fixture(autouse=True)
    def _terminal_size(self, monkeypatch: pytest.MonkeyPatch):
        class TerminalSize:
            columns = 10

        terminalsize = TerminalSize()
        monkeypatch.setattr("streamlink_cli.utils.terminal.get_terminal_size", lambda: terminalsize)

    @pytest.fixture
    def stream(self):
        return StringIO()

    @pytest.fixture
    def output(self, stream: StringIO):
        yield TerminalOutput(stream)

    @posix_only
    def test_print_posix(self, output: TerminalOutput, stream: StringIO):
        output.print_inplace("foo")
        output.print_inplace("barbaz")
        output.print_inplace("0123456789")
        output.print_inplace("abcdefghijk")
        output.end()
        assert stream.getvalue() == "\rfoo       \rbarbaz    \r0123456789\rabcdefghijk\n"

    @windows_only
    def test_print_windows(self, output: TerminalOutput, stream: StringIO):
        output.print_inplace("foo")
        output.print_inplace("barbaz")
        output.print_inplace("0123456789")
        output.print_inplace("abcdefghijk")
        output.end()
        assert stream.getvalue() == "\rfoo      \rbarbaz   \r0123456789\rabcdefghijk\n"
