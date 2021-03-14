import unittest
from unittest.mock import Mock, patch

from streamlink.compat import is_win32
from tests.test_cmdline import CommandLineTestCase


@unittest.skipIf(is_win32, "test only applicable in a POSIX OS")
@patch("streamlink_cli.main.NamedPipe", Mock(return_value=Mock(path="/tmp/streamlinkpipe")))
class TestCommandLineWithPlayerFifoPosix(CommandLineTestCase):
    def test_player_fifo_default(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "any-player",
             "http://test.se", "test"],
            ["any-player", "/tmp/streamlinkpipe"]
        )


@unittest.skipIf(not is_win32, "test only applicable on Windows")
@patch("streamlink_cli.main.NamedPipe", Mock(return_value=Mock(path="\\\\.\\pipe\\streamlinkpipe")))
class TestCommandLineWithPlayerFifoWindows(CommandLineTestCase):
    def test_player_fifo_default(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "any-player.exe",
             "http://test.se", "test"],
            "any-player.exe \\\\.\\pipe\\streamlinkpipe"
        )

    def test_player_fifo_vlc(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "C:\\Program Files\\VideoLAN\\vlc.exe",
             "http://test.se", "test"],
            "C:\\Program Files\\VideoLAN\\vlc.exe --input-title-format http://test.se stream://\\\\\\.\\pipe\\streamlinkpipe"
        )

    def test_player_fifo_mpv(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "C:\\Program Files\\mpv\\mpv.exe",
             "http://test.se", "test"],
            "C:\\Program Files\\mpv\\mpv.exe --force-media-title=http://test.se file://\\\\.\\pipe\\streamlinkpipe"
        )
