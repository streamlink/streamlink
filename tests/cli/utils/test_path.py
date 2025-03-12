from __future__ import annotations

from pathlib import Path
from string import ascii_lowercase as alphabet

import pytest

from streamlink_cli.utils.path import replace_chars, replace_path, truncate_path


@pytest.mark.parametrize("char", list(range(32)))
def test_replace_chars_unprintable(char: int):
    assert replace_chars(f"foo{chr(char)}{chr(char)}bar") == "foo_bar", "Replaces unprintable characters"


@pytest.mark.posix_only()
@pytest.mark.parametrize("char", "/".split())
def test_replace_chars_posix(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@pytest.mark.windows_only()
@pytest.mark.parametrize("char", '\x7f"*/:<>?\\|'.split())
def test_replace_chars_windows(char: str):
    assert replace_chars(f"foo{char}{char}bar") == "foo_bar", "Replaces multiple unsupported characters in a row"


@pytest.mark.posix_only()
def test_replace_chars_posix_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + "/") == "_"


@pytest.mark.windows_only()
def test_replace_chars_windows_all():
    assert replace_chars("".join(chr(i) for i in range(32)) + '\x7f"*/:<>?\\|') == "_"


@pytest.mark.posix_only()
def test_replace_chars_posix_override():
    all_chars = "".join(chr(i) for i in range(32)) + '\x7f"*:/<>?\\|'
    assert replace_chars(all_chars) == '_\x7f"*:_<>?\\|'
    assert replace_chars(all_chars, "posix") == '_\x7f"*:_<>?\\|'
    assert replace_chars(all_chars, "unix") == '_\x7f"*:_<>?\\|'
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


@pytest.mark.windows_only()
def test_replace_chars_windows_override():
    all_chars = "".join(chr(i) for i in range(32)) + '\x7f"*:/<>?\\|'
    assert replace_chars(all_chars) == "_"
    assert replace_chars(all_chars, "posix") == '_\x7f"*:_<>?\\|'
    assert replace_chars(all_chars, "unix") == '_\x7f"*:_<>?\\|'
    assert replace_chars(all_chars, "windows") == "_"
    assert replace_chars(all_chars, "win32") == "_"


def test_replace_chars_replacement():
    assert replace_chars("\x00", None, "+") == "+"


def test_replace_path():
    def mapper(s, *_):
        return dict(foo=".", bar="..").get(s, s)

    path = Path("foo", ".", "bar", "..", "baz")
    expected = Path("_", ".", "_", "..", "baz")
    assert replace_path(path, mapper) == expected, "Only replaces mapped parts which are in the special parts tuple"


@pytest.mark.posix_only()
@pytest.mark.parametrize("os_environ", [pytest.param({"HOME": "/home/foo"}, id="posix")], indirect=True)
def test_replace_path_expanduser_posix(os_environ):
    assert replace_path("~/bar", lambda s, *_: s) == Path("/home/foo/bar")
    assert replace_path("foo/bar", lambda s, *_: dict(foo="~").get(s, s)) == Path("~/bar")


@pytest.mark.windows_only()
@pytest.mark.parametrize("os_environ", [pytest.param({"USERPROFILE": "C:\\Users\\foo"}, id="windows")], indirect=True)
def test_replace_path_expanduser_windows(os_environ):
    assert replace_path("~\\bar", lambda s, *_: s) == Path("C:\\Users\\foo\\bar")
    assert replace_path("foo\\bar", lambda s, *_: dict(foo="~").get(s, s)) == Path("~\\bar")


bear = "🐻"  # Unicode character: "Bear Face" (U+1F43B)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        pytest.param(
            (alphabet, 255, True),
            alphabet,
            id="text - no truncation",
        ),
        pytest.param(
            (alphabet * 10, 255, True),
            (alphabet * 10)[:255],
            id="text - truncate",
        ),
        pytest.param(
            (alphabet * 10, 50, True),
            (alphabet * 10)[:50],
            id="text - truncate at 50",
        ),
        pytest.param(
            (f"{alphabet}.ext", 255, True),
            f"{alphabet}.ext",
            id="text+ext1 - no truncation",
        ),
        pytest.param(
            (f"{alphabet * 10}.ext", 255, True),
            f"{(alphabet * 10)[:251]}.ext",
            id="text+ext1 - truncate",
        ),
        pytest.param(
            (f"{alphabet * 10}.ext", 50, True),
            f"{(alphabet * 10)[:46]}.ext",
            id="text+ext1 - truncate at 50",
        ),
        pytest.param(
            (f"{alphabet * 10}.ext", 255, False),
            (alphabet * 10)[:255],
            id="text+ext1+nokeep - truncate",
        ),
        pytest.param(
            (f"{alphabet * 10}.ext", 50, False),
            (alphabet * 10)[:50],
            id="text+ext1+nokeep - truncate at 50",
        ),
        pytest.param(
            (f"{alphabet * 10}.notafilenameextension", 255, True),
            (alphabet * 10)[:255],
            id="text+ext2 - truncate",
        ),
        pytest.param(
            (f"{alphabet * 10}.notafilenameextension", 50, True),
            (alphabet * 10)[:50],
            id="text+ext2 - truncate at 50",
        ),
        pytest.param(
            (bear * 63, 255, True),
            bear * 63,
            id="bear - no truncation",
        ),
        pytest.param(
            (bear * 64, 255, True),
            bear * 63,
            id="bear - truncate",
        ),
        pytest.param(
            (bear * 64, 50, True),
            bear * 12,
            id="bear - truncate at 50",
        ),
        pytest.param(
            (f"{bear}.ext", 255, True),
            f"{bear}.ext",
            id="bear+ext1 - no truncation",
        ),
        pytest.param(
            (f"{bear * 64}.ext", 255, True),
            f"{bear * 62}.ext",
            id="bear+ext1 - truncate",
        ),
        pytest.param(
            (f"{bear * 64}.ext", 50, True),
            f"{bear * 11}.ext",
            id="bear+ext1 - truncate at 50",
        ),
        pytest.param(
            (f"{bear * 64}.ext", 255, False),
            bear * 63,
            id="bear+ext1+nokeep - truncate",
        ),
        pytest.param(
            (f"{bear * 64}.ext", 50, False),
            bear * 12,
            id="bear+ext1+nokeep - truncate at 50",
        ),
        pytest.param(
            (f"{bear * 64}.notafilenameextension", 255, True),
            bear * 63,
            id="bear+ext2 - truncate",
        ),
        pytest.param(
            (f"{bear * 64}.notafilenameextension", 50, True),
            bear * 12,
            id="bear+ext2 - truncate at 50",
        ),
    ],
)
def test_truncate_path(args: tuple[str, int, bool], expected: str):
    path, length, keep_extension = args
    result = truncate_path(path, length, keep_extension)
    assert len(result.encode("utf-8")) <= length
    assert result == expected
