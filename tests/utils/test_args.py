import unittest
from argparse import ArgumentTypeError

import pytest

from streamlink.utils.args import boolean, comma_list, comma_list_filter, filesize, keyvalue, num


class TestUtilsArgs(unittest.TestCase):
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

    def test_num(self):
        # (value, func, result)
        test_data = [
            ("33", num(int, 5, 120), 33),
            ("234", num(int, min=10), 234),
            ("50.222", num(float, 10, 120), 50.222),
        ]

        for _v, _f, _r in test_data:
            assert _f(_v) == _r

    def test_num_error(self):
        func = num(int, 5, 10)
        with pytest.raises(ArgumentTypeError):
            func("3")

        func = num(int, max=11)
        with pytest.raises(ArgumentTypeError):
            func("12")

        func = num(int, min=15)
        with pytest.raises(ArgumentTypeError):
            func("8")

        func = num(float, 10, 20)
        with pytest.raises(ArgumentTypeError):
            func("40.222")
