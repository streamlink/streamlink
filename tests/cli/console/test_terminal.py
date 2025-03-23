from typing import NamedTuple

import pytest

from streamlink_cli.console.terminal import cut_text, term_width, text_width


@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(144, id="non-windows", marks=pytest.mark.posix_only()),
        pytest.param(143, id="windows", marks=pytest.mark.windows_only()),
    ],
)
def test_term_width(monkeypatch: pytest.MonkeyPatch, expected: int):
    class TerminalSize(NamedTuple):
        columns: int
        rows: int

    monkeypatch.setattr("streamlink_cli.console.terminal.get_terminal_size", lambda: TerminalSize(columns=144, rows=42))

    assert term_width() == expected


@pytest.mark.parametrize(
    ("chars", "expected"),
    [
        ("ABCDEFGHIJ", 10),
        ("A你好世界こんにちは안녕하세요B", 30),
        ("·「」『』【】-=！@#￥%……&×（）", 30),  # noqa: RUF001
    ],
)
def test_text_width(chars, expected):
    assert text_width(chars) == expected


@pytest.mark.parametrize(
    ("prefix", "max_len", "expected"),
    [
        ("你好世界こんにちは안녕하세요CD", 10, "녕하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 9, "하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 23, "こんにちは안녕하세요CD"),
    ],
)
def test_cut_text(prefix, max_len, expected):
    assert cut_text(prefix, max_len) == expected
