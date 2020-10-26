import unittest
from unittest.mock import PropertyMock, patch

import pytest

from streamlink import StreamError
from streamlink import Streamlink
from streamlink.stream import StreamProcess


@pytest.mark.parametrize("parameters,arguments,expected", [
    (dict(h=True), None, ["test", "-h"]),
    (dict(foo="bar"), None, ["test", "--foo", "bar"]),
    (dict(L="big"), None, ["test", "-L", "big"]),
    (None, ["foo", "bar"], ["test", "foo", "bar"]),
    (dict(extra="nothing", verbose=True, L="big"), None, ["test", "-L", "big", "--extra", "nothing", "--verbose"]),
    (dict(extra=["a", "b", "c"]), None, ["test", "--extra", "a", "--extra", "b", "--extra", "c"]),
    (dict(e=["a", "b", "c"]), None, ["test", "-e", "a", "-e", "b", "-e", "c"]),
])
def test_bake(parameters, arguments, expected):
    assert expected == StreamProcess.bake("test", parameters or {}, arguments or [])


class TestStreamProcess(unittest.TestCase):

    def test_bake_different_prefix(self):
        self.assertEqual(["test", "/H", "/foo", "bar", "/help"],
                         StreamProcess.bake("test", dict(help=True, H=True, foo="bar"),
                                            long_option_prefix="/", short_option_prefix="/"))

        self.assertEqual(["test", "/?"],
                         StreamProcess.bake("test", {"?": True},
                                            long_option_prefix="/", short_option_prefix="/"))

    @patch('streamlink.stream.streamprocess.StreamProcess.cmd', new_callable=PropertyMock)
    def test_check_cmd_none(self, mock_cmd):
        s = StreamProcess(Streamlink())
        mock_cmd.return_value = None
        self.assertRaises(StreamError, s._check_cmd)

    @patch('streamlink.stream.streamprocess.which')
    @patch('streamlink.stream.streamprocess.StreamProcess.cmd', new_callable=PropertyMock)
    def test_check_cmd_cat(self, which, mock_cmd):
        s = StreamProcess(Streamlink())
        mock_cmd.return_value = "test"
        self.assertEqual("test", s._check_cmd())

    @patch('streamlink.stream.streamprocess.which')
    @patch('streamlink.stream.streamprocess.StreamProcess.cmd', new_callable=PropertyMock)
    def test_check_cmd_nofound(self, which, mock_cmd):
        s = StreamProcess(Streamlink())
        mock_cmd.return_value = "test"
        which.return_value = None
        self.assertRaises(StreamError, s._check_cmd)

    @patch('streamlink.stream.streamprocess.which')
    @patch('streamlink.stream.streamprocess.StreamProcess.cmd', new_callable=PropertyMock)
    def test_check_cmdline(self, which, mock_cmd):
        s = StreamProcess(Streamlink(), params=dict(help=True))
        mock_cmd.return_value = "test"
        which.return_value = "test"
        self.assertEqual("test --help", s.cmdline())

    @patch('streamlink.stream.streamprocess.which')
    @patch('streamlink.stream.streamprocess.StreamProcess.cmd', new_callable=PropertyMock)
    def test_check_cmdline_long(self, which, mock_cmd):
        s = StreamProcess(Streamlink(), params=dict(out_file="test file.txt"))
        mock_cmd.return_value = "test"
        which.return_value = "test"
        self.assertEqual("test --out-file \"test file.txt\"", s.cmdline())
