import os
from pathlib import Path
from unittest.mock import patch

import pytest

from streamlink_cli.utils.path import replace_chars, replace_path


@pytest.mark.parametrize("char", list(range(32)))
def test_replace_chars_unprintable(char: int):
    assert replace_chars(f"foo{chr(char)}{chr(char)}bar") == "foo_bar", "Replaces unprintable characters"


@pytest.mark.posix_only()
@pytest.mark.parametrize("char", "/".split())
def test_replace_chars_posix(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@pytest.mark.windows_only()
@pytest.mark.parametrize("char", "\x7f\"*/:<>?\\|".split())
def test_replace_chars_windows(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@pytest.mark.posix_only()
def test_replace_chars_posix_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + "/") == "_"


@pytest.mark.windows_only()
def test_replace_chars_windows_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + "\x7f\"*/:<>?\\|") == "_"


@pytest.mark.posix_only()
def test_replace_chars_posix_override():
    all_chars = "".join(chr(i) for i in range(32)) + "\x7f\"*:/<>?\\|"
    assert replace_chars(all_chars) == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "posix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "unix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


@pytest.mark.windows_only()
def test_replace_chars_windows_override():
    all_chars = "".join(chr(i) for i in range(32)) + "\x7f\"*:/<>?\\|"
    assert replace_chars(all_chars) == "_"
    assert replace_chars(all_chars, "posix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "unix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


def test_replace_chars_replacement():
    assert replace_chars("\x00", None, "+") == "+"


def test_replace_path():
    def mapper(s):
        return dict(foo=".", bar="..").get(s, s)

    path = Path("foo", ".", "bar", "..", "baz")
    expected = Path("_", ".", "_", "..", "baz")
    assert replace_path(path, mapper) == expected, "Only replaces mapped parts which are in the special parts tuple"


@pytest.mark.posix_only()
def test_replace_path_expanduser_posix():
    with patch.object(os, "environ", {"HOME": "/home/foo"}):
        assert replace_path("~/bar", lambda s: s) == Path("/home/foo/bar")
        assert replace_path("foo/bar", lambda s: dict(foo="~").get(s, s)) == Path("~/bar")


@pytest.mark.windows_only()
def test_replace_path_expanduser_windows():
    with patch.object(os, "environ", {"USERPROFILE": "C:\\Users\\foo"}):
        assert replace_path("~\\bar", lambda s: s) == Path("C:\\Users\\foo\\bar")
        assert replace_path("foo\\bar", lambda s: dict(foo="~").get(s, s)) == Path("~\\bar")
