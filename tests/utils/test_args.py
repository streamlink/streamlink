import unittest
from argparse import ArgumentTypeError

from streamlink.utils.args import (
    boolean, comma_list, comma_list_filter, filesize, keyvalue, num
)


class TestUtilsArgs(unittest.TestCase):
    def test_boolean_true(self):
        self.assertEqual(boolean('1'), True)
        self.assertEqual(boolean('on'), True)
        self.assertEqual(boolean('true'), True)
        self.assertEqual(boolean('yes'), True)
        self.assertEqual(boolean('Yes'), True)

    def test_boolean_false(self):
        self.assertEqual(boolean('0'), False)
        self.assertEqual(boolean('false'), False)
        self.assertEqual(boolean('no'), False)
        self.assertEqual(boolean('No'), False)
        self.assertEqual(boolean('off'), False)

    def test_boolean_error(self):
        with self.assertRaises(ArgumentTypeError):
            boolean('yesno')

        with self.assertRaises(ArgumentTypeError):
            boolean('FOO')

        with self.assertRaises(ArgumentTypeError):
            boolean('2')

    def test_comma_list(self):
        # (values, result)
        test_data = [
            ('foo.bar,example.com', ['foo.bar', 'example.com']),
            ('/var/run/foo,/var/run/bar', ['/var/run/foo', '/var/run/bar']),
            ('foo bar,24', ['foo bar', '24']),
            ('hls', ['hls']),
        ]

        for _v, _r in test_data:
            self.assertEqual(comma_list(_v), _r)

    def test_comma_list_filter(self):
        # (acceptable, values, result)
        test_data = [
            (['foo', 'bar', 'com'], 'foo,bar,example.com', ['foo', 'bar']),
            (['/var/run/foo', 'FO'], '/var/run/foo,/var/run/bar',
             ['/var/run/foo']),
            (['hls', 'hls5', 'dash'], 'hls,hls5', ['hls', 'hls5']),
            (['EU', 'RU'], 'DE,FR,RU,US', ['RU']),
        ]

        for _a, _v, _r in test_data:
            func = comma_list_filter(_a)
            self.assertEqual(func(_v), _r)

    def test_filesize(self):
        self.assertEqual(filesize('2000'), 2000)
        self.assertEqual(filesize('11KB'), 1024 * 11)
        self.assertEqual(filesize('12MB'), 1024 * 1024 * 12)
        self.assertEqual(filesize('1KB'), 1024)
        self.assertEqual(filesize('1MB'), 1024 * 1024)
        self.assertEqual(filesize('2KB'), 1024 * 2)

    def test_filesize_error(self):
        with self.assertRaises(ValueError):
            filesize('FOO')

        with self.assertRaises(ValueError):
            filesize('0.00000')

    def test_keyvalue(self):
        # (value, result)
        test_data = [
            ('X-Forwarded-For=127.0.0.1', ('X-Forwarded-For', '127.0.0.1')),
            ('Referer=https://foo.bar', ('Referer', 'https://foo.bar')),
            (
                'User-Agent=Mozilla/5.0 (X11; Linux x86_64; rv:60.0)'
                ' Gecko/20100101 Firefox/60.0',
                ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) '
                 'Gecko/20100101 Firefox/60.0')
            ),
            ('domain=example.com', ('domain', 'example.com')),
        ]

        for _v, _r in test_data:
            self.assertEqual(keyvalue(_v), _r)

    def test_keyvalue_error(self):
        with self.assertRaises(ValueError):
            keyvalue('127.0.0.1')

    def test_num(self):
        # (value, func, result)
        test_data = [
            ('33', num(int, 5, 120), 33),
            ('234', num(int, min=10), 234),
            ('50.222', num(float, 10, 120), 50.222),
        ]

        for _v, _f, _r in test_data:
            self.assertEqual(_f(_v), _r)

    def test_num_error(self):
        with self.assertRaises(ArgumentTypeError):
            func = num(int, 5, 10)
            func('3')

        with self.assertRaises(ArgumentTypeError):
            func = num(int, max=11)
            func('12')

        with self.assertRaises(ArgumentTypeError):
            func = num(int, min=15)
            func('8')

        with self.assertRaises(ArgumentTypeError):
            func = num(float, 10, 20)
            func('40.222')
