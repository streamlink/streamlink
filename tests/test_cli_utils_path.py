import pytest

from streamlink_cli.utils.path import replace_chars
from tests import posix_only, windows_only


@pytest.mark.parametrize("char", [i for i in range(32)])
def test_replace_chars_unprintable(char: int):
    assert replace_chars(f"foo{chr(char)}{chr(char)}bar") == "foo_bar", "Replaces unprintable characters"


@posix_only
@pytest.mark.parametrize("char", "/".split())
def test_replace_chars_posix(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@windows_only
@pytest.mark.parametrize("char", "\x7f\"*/:<>?\\|".split())
def test_replace_chars_windows(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@posix_only
def test_replace_chars_posix_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + "/") == "_"


@windows_only
def test_replace_chars_windows_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + "\x7f\"*/:<>?\\|") == "_"


@posix_only
def test_replace_chars_posix_override():
    all_chars = "".join(chr(i) for i in range(32)) + "\x7f\"*:/<>?\\|"
    assert replace_chars(all_chars) == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "posix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "unix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


@windows_only
def test_replace_chars_windows_override():
    all_chars = "".join(chr(i) for i in range(32)) + "\x7f\"*:/<>?\\|"
    assert replace_chars(all_chars) == "_"
    assert replace_chars(all_chars, "posix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "unix") == "_\x7f\"*:_<>?\\|"
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


def test_replace_chars_replacement():
    assert replace_chars("\x00", None, "+") == "+"
