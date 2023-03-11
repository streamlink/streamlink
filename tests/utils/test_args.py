from argparse import ArgumentTypeError
from contextlib import nullcontext
from typing import Type

import pytest

from streamlink.utils.args import boolean, comma_list, comma_list_filter, filesize, keyvalue, num


does_not_raise = nullcontext()


class TestUtilsArgs:
    def test_boolean_true(self):
        assert boolean("1") is True
        assert boolean("on") is True
        assert boolean("true") is True
        assert boolean("yes") is True
        assert boolean("Yes") is True

    def test_boolean_false(self):
        assert boolean("0") is False
        assert boolean("false") is False
        assert boolean("no") is False
        assert boolean("No") is False
        assert boolean("off") is False

    def test_boolean_error(self):
        with pytest.raises(ArgumentTypeError):
            boolean("yesno")
        with pytest.raises(ArgumentTypeError):
            boolean("FOO")
        with pytest.raises(ArgumentTypeError):
            boolean("2")

    def test_comma_list(self):
        # (values, result)
        test_data = [
            ("foo.bar,example.com", ["foo.bar", "example.com"]),
            ("/var/run/foo,/var/run/bar", ["/var/run/foo", "/var/run/bar"]),
            ("foo bar,24", ["foo bar", "24"]),
            ("hls", ["hls"]),
        ]

        for _v, _r in test_data:
            assert comma_list(_v) == _r

    def test_comma_list_filter(self):
        # (acceptable, values, result)
        test_data = [
            (["foo", "bar", "com"], "foo,bar,example.com", ["foo", "bar"]),
            (["/var/run/foo", "FO"], "/var/run/foo,/var/run/bar",
             ["/var/run/foo"]),
            (["hls", "hls5", "dash"], "hls,hls5", ["hls", "hls5"]),
            (["EU", "RU"], "DE,FR,RU,US", ["RU"]),
        ]

        for _a, _v, _r in test_data:
            func = comma_list_filter(_a)
            assert func(_v) == _r

    def test_filesize(self):
        assert filesize("2000") == 2000
        assert filesize("11KB") == 1024 * 11
        assert filesize("12MB") == 1024 * 1024 * 12
        assert filesize("1KB") == 1024
        assert filesize("1MB") == 1024 * 1024
        assert filesize("2KB") == 1024 * 2

    def test_filesize_error(self):
        with pytest.raises(ValueError):  # noqa: PT011
            filesize("FOO")
        with pytest.raises(ValueError):  # noqa: PT011
            filesize("0.00000")

    def test_keyvalue(self):
        # (value, result)
        test_data = [
            ("X-Forwarded-For=127.0.0.1", ("X-Forwarded-For", "127.0.0.1")),
            ("Referer=https://foo.bar", ("Referer", "https://foo.bar")),
            (
                "User-Agent=Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0",
                ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"),
            ),
            ("domain=example.com", ("domain", "example.com")),
        ]

        for _v, _r in test_data:
            assert keyvalue(_v) == _r

    def test_keyvalue_error(self):
        with pytest.raises(ValueError):  # noqa: PT011
            keyvalue("127.0.0.1")


class TestNum:
    @pytest.mark.parametrize(("numtype", "value", "expected", "raises"), [
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
    ])
    def test_numtype(self, numtype: Type[float], value: float, expected: float, raises: nullcontext):
        func = num(numtype)
        assert func.__name__ == numtype.__name__
        with raises:
            result = func(value)
            assert type(result) is numtype
            assert result == expected

    @pytest.mark.parametrize(("operators", "value", "raises"), [
        ({"ge": 1}, 1, does_not_raise),
        ({"ge": 0}, 1, does_not_raise),
        ({"gt": 0}, 1, does_not_raise),
        ({"le": 1}, 1, does_not_raise),
        ({"le": 2}, 1, does_not_raise),
        ({"lt": 2}, 1, does_not_raise),
        ({"ge": 1, "gt": 0, "le": 1, "lt": 2}, 1, does_not_raise),
        ({"ge": 2}, 1, pytest.raises(ArgumentTypeError, match=r"^int value must be >=2, but is 1$")),
        ({"gt": 1}, 1, pytest.raises(ArgumentTypeError, match=r"^int value must be >1, but is 1$")),
        ({"le": 0}, 1, pytest.raises(ArgumentTypeError, match=r"^int value must be <=0, but is 1$")),
        ({"lt": 1}, 1, pytest.raises(ArgumentTypeError, match=r"^int value must be <1, but is 1$")),
        ({"ge": 1, "gt": 0, "le": 0, "lt": 2}, 1, pytest.raises(ArgumentTypeError, match=r"^int value must be <=0, but is 1$")),
    ])
    def test_operator(self, operators: dict, value: float, raises: nullcontext):
        with raises:
            assert num(int, **operators)(value) == value
