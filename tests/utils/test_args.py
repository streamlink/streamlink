from __future__ import annotations

import argparse
from contextlib import nullcontext
from operator import attrgetter
from typing import TYPE_CHECKING

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.utils.args import Boolean, boolean, comma_list, comma_list_filter, filesize, keyvalue, num


if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


does_not_raise = nullcontext()


class TestBooleanAction:
    @pytest.fixture()
    def parser(self):
        return argparse.ArgumentParser(exit_on_error=False)

    @pytest.mark.parametrize(
        ("argv", "one", "two"),
        [
            pytest.param([], None, True, id="defaults"),
            pytest.param(["--one", "--two"], True, True, id="positive"),
            pytest.param(["--other", "--two"], True, True, id="positive-alt"),
            pytest.param(["--no-one", "--no-two"], False, False, id="negative"),
            pytest.param(["--no-other", "--no-two"], False, False, id="negative-alt"),
        ],
    )
    def test_no_values(self, parser: argparse.ArgumentParser, argv: list[str], one: bool, two: bool):
        parser.add_argument("--one", "--other", action=Boolean)
        parser.add_argument("--two", action=Boolean, default=True)
        namespace = parser.parse_args(argv)
        assert namespace.one is one
        assert namespace.two is two

    @pytest.mark.parametrize(
        "transform",
        [
            pytest.param(str.lower, id="lower"),
            pytest.param(str.upper, id="upper"),
        ],
    )
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1", True),
            ("on", True),
            ("true", True),
            ("yes", True),
            ("0", False),
            ("off", False),
            ("false", False),
            ("no", False),
        ],
    )
    def test_value(
        self,
        recwarn: pytest.WarningsRecorder,
        parser: argparse.ArgumentParser,
        value: str,
        transform: Callable,
        expected: bool,
    ):
        parser.add_argument("--param", action=Boolean, nargs="?")
        namespace = parser.parse_args(["--param", transform(value)])
        assert namespace.param is expected
        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (StreamlinkDeprecationWarning, f"--param={transform(value)} is deprecated. Use --param/--no-param instead."),
        ]

    def test_value_empty(self, parser: argparse.ArgumentParser):
        parser.add_argument("--param", action=Boolean, nargs="?")
        namespace = parser.parse_args(["--param"])
        assert namespace.param is True

    @pytest.mark.parametrize(
        ("argv", "raises"),
        [
            pytest.param(
                ["--param="],
                pytest.raises(argparse.ArgumentError, match=r"Invalid argument value"),
                id="missing-value",
            ),
            pytest.param(
                ["--param=foo"],
                pytest.raises(argparse.ArgumentError, match=r"Invalid argument value"),
                id="invalid-value",
            ),
            pytest.param(
                ["--no-param=on"],
                pytest.raises(argparse.ArgumentError, match=r"Argument value set on a negated argument name"),
                id="negated-value",
            ),
        ],
    )
    def test_value_errors(self, parser: argparse.ArgumentParser, argv: list[str], raises: nullcontext):
        parser.add_argument("--param", action=Boolean, nargs="?")
        with raises:
            parser.parse_args(argv)

    def test_optional_value_with_positional_after(self, parser: argparse.ArgumentParser):
        """
        argparse optionals with nargs='?', '*' or '+' can't be followed by positionals
        https://github.com/python/cpython/issues/53584
        """
        parser.add_argument("--foo", action=Boolean, nargs="?")
        parser.add_argument("bar")

        attrs = attrgetter("foo", "bar")
        for argv in (["--foo", "1", "value"], ["--foo=1", "value"]):
            with pytest.warns(StreamlinkDeprecationWarning, match=r"^--foo=1 is deprecated\. Use --foo/--no-foo instead\.$"):
                assert attrs(parser.parse_args(argv)) == (True, "value")

        with pytest.raises(argparse.ArgumentError, match=r"Invalid argument value"):
            parser.parse_args(["--foo", "value"])


@pytest.mark.parametrize(
    ("value", "expected", "raises"),
    [
        ("1", True, does_not_raise),
        ("on", True, does_not_raise),
        ("true", True, does_not_raise),
        ("yes", True, does_not_raise),
        ("YES", True, does_not_raise),
        ("0", False, does_not_raise),
        ("off", False, does_not_raise),
        ("false", False, does_not_raise),
        ("no", False, does_not_raise),
        ("NO", False, does_not_raise),
        ("invalid", None, pytest.raises(ValueError, match=r"invalid is not one of .+")),
        ("2", None, pytest.raises(ValueError, match=r"2 is not one of .+")),
    ],
)
def test_boolean(value: str, expected: bool, raises: nullcontext):
    with raises:
        assert boolean(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("foo", ["foo"], id="single item"),
        pytest.param("foo.bar,example.com", ["foo.bar", "example.com"], id="separator"),
        pytest.param("/var/run/foo,/var/run/bar", ["/var/run/foo", "/var/run/bar"], id="paths"),
        pytest.param("foo bar,baz", ["foo bar", "baz"], id="whitespace"),
    ],
)
def test_comma_list(value: str, expected: list[str]):
    assert comma_list(value) == expected


@pytest.mark.parametrize(
    ("options", "value", "expected"),
    [
        pytest.param(
            {"acceptable": ["foo", "bar"]},
            "foo,bar,baz,qux",
            ["foo", "bar"],
            id="superset",
        ),
        pytest.param(
            {"acceptable": ["foo", "bar", "baz"]},
            "foo,bar",
            ["foo", "bar"],
            id="subset",
        ),
        pytest.param(
            {"acceptable": ["foo", "bar"], "unique": True},
            "foo,bar,baz,foo,bar,baz",
            ["bar", "foo"],
            id="unique",
        ),
    ],
)
def test_comma_list_filter(options: dict, value: str, expected: list[str]):
    func = comma_list_filter(**options)
    assert func(value) == expected


def test_comma_list_filter_hashable():
    assert hash(comma_list_filter(["1", "2"])) != hash(comma_list_filter(["1", "2", "3"]))
    assert hash(comma_list_filter(["1", "2"], unique=True)) == hash(comma_list_filter(["1", "2"], unique=True))
    assert hash(comma_list_filter(["1", "2"], unique=True)) != hash(comma_list_filter(["1", "2"], unique=False))


@pytest.mark.parametrize(
    ("value", "expected", "raises"),
    [
        ("12345", 12345, does_not_raise),
        ("123.45", int(123.45), does_not_raise),
        ("1KB", 1 * 2**10, does_not_raise),
        ("123kB", 123 * 2**10, does_not_raise),
        ("123.45kB", int(123.45 * 2**10), does_not_raise),
        ("1mb", 1 * 2**20, does_not_raise),
        ("123k", 123 * 2**10, does_not_raise),
        ("123M", 123 * 2**20, does_not_raise),
        ("123.45M", int(123.45 * 2**20), does_not_raise),
        ("  123.45MB  ", int(123.45 * 2**20), does_not_raise),
        ("FOO", None, pytest.raises(ValueError, match=r"^Invalid file size format$")),
        ("0", None, pytest.raises(ValueError, match=r"^int value must be >=1, but is 0$")),
        ("0.00000", None, pytest.raises(ValueError, match=r"^int value must be >=1, but is 0$")),
    ],
)
def test_filesize(value: str, expected: int, raises: nullcontext):
    with raises:
        assert filesize(value) == expected


@pytest.mark.parametrize(
    ("value", "expected", "raises"),
    [
        pytest.param(
            "X-Forwarded-For=127.0.0.1",
            ("X-Forwarded-For", "127.0.0.1"),
            does_not_raise,
            id="separator",
        ),
        pytest.param(
            "foo=bar=baz",
            ("foo", "bar=baz"),
            does_not_raise,
            id="value with separator",
        ),
        pytest.param(
            "foo=",
            ("foo", ""),
            does_not_raise,
            id="missing value",
        ),
        pytest.param(
            "  foo  =  bar  ",
            ("foo", "bar  "),
            does_not_raise,
            id="whitespace",
        ),
        pytest.param(
            "User-Agent=Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0",
            ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"),
            does_not_raise,
            id="user-agent",
        ),
        pytest.param(
            "127.0.0.1",
            None,
            pytest.raises(ValueError, match=r"^Invalid key=value format$"),
            id="invalid format",
        ),
        pytest.param(
            "=value",
            None,
            pytest.raises(ValueError, match=r"^Invalid key=value format$"),
            id="missing key",
        ),
    ],
)
def test_keyvalue(value: str, expected: Sequence[str], raises: nullcontext):
    with raises:
        assert keyvalue(value) == expected


class TestNum:
    @pytest.mark.parametrize(
        ("numtype", "value", "expected", "raises"),
        [
            (int, 123, 123, does_not_raise),
            (float, 123, 123.0, does_not_raise),
            (int, 123.456, 123, does_not_raise),
            (int, "123", 123, does_not_raise),
            (int, "-123", -123, does_not_raise),
            (float, "123.456", 123.456, does_not_raise),
            (float, "3.1415e2", 314.15, does_not_raise),
            (int, "", None, pytest.raises(ValueError, match=r"^invalid literal for int\(\) with base 10:")),
            (int, ".", None, pytest.raises(ValueError, match=r"^invalid literal for int\(\) with base 10:")),
            (int, "-", None, pytest.raises(ValueError, match=r"^invalid literal for int\(\) with base 10:")),
            (int, "foo", None, pytest.raises(ValueError, match=r"^invalid literal for int\(\) with base 10:")),
            (float, "", None, pytest.raises(ValueError, match=r"^could not convert string to float:")),
            (float, ".", None, pytest.raises(ValueError, match=r"^could not convert string to float:")),
            (float, "-", None, pytest.raises(ValueError, match=r"^could not convert string to float:")),
            (float, "foo", None, pytest.raises(ValueError, match=r"^could not convert string to float:")),
        ],
    )
    def test_numtype(self, numtype: type[float], value: float, expected: float, raises: nullcontext):
        func = num(numtype)
        assert func.__name__ == numtype.__name__
        with raises:
            result = func(value)
            assert type(result) is numtype
            assert result == expected

    @pytest.mark.parametrize(
        ("operators", "value", "raises"),
        [
            ({"ge": 1}, 1, does_not_raise),
            ({"ge": 0}, 1, does_not_raise),
            ({"gt": 0}, 1, does_not_raise),
            ({"le": 1}, 1, does_not_raise),
            ({"le": 2}, 1, does_not_raise),
            ({"lt": 2}, 1, does_not_raise),
            ({"ge": 1, "gt": 0, "le": 1, "lt": 2}, 1, does_not_raise),
            ({"ge": 2}, 1, pytest.raises(ValueError, match=r"^int value must be >=2, but is 1$")),
            ({"gt": 1}, 1, pytest.raises(ValueError, match=r"^int value must be >1, but is 1$")),
            ({"le": 0}, 1, pytest.raises(ValueError, match=r"^int value must be <=0, but is 1$")),
            ({"lt": 1}, 1, pytest.raises(ValueError, match=r"^int value must be <1, but is 1$")),
            ({"ge": 1, "gt": 0, "le": 0, "lt": 2}, 1, pytest.raises(ValueError, match=r"^int value must be <=0, but is 1$")),
        ],
    )
    def test_operator(self, operators: dict, value: float, raises: nullcontext):
        with raises:
            assert num(int, **operators)(value) == value

    def test_hashable(self):
        assert hash(num(int, ge=1)) == hash(num(int, ge=1))
        assert hash(num(float, ge=1.0)) == hash(num(float, ge=1.0))
        assert hash(num(int, ge=1)) != hash(num(int, gt=1))
        assert hash(num(int, ge=1)) != hash(num(int, le=1))
        assert hash(num(int, ge=1)) != hash(num(int, lt=1))
        assert hash(num(int, ge=1)) != hash(num(float, ge=1.0))
