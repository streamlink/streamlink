from unittest.mock import Mock, patch

from tests import posix_only, windows_only
from tests.cli.test_cmdline import CommandLineTestCase


@posix_only
@patch("streamlink_cli.main.NamedPipe", Mock(return_value=Mock(path="/tmp/streamlinkpipe")))
class TestCommandLineWithPlayerFifoPosix(CommandLineTestCase):
    def test_player_fifo_default(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "any-player",
             "http://test.se", "test"],
            ["any-player", "/tmp/streamlinkpipe"],
        )


@windows_only
@patch("streamlink_cli.main.NamedPipe", Mock(return_value=Mock(path="\\\\.\\pipe\\streamlinkpipe")))
class TestCommandLineWithPlayerFifoWindows(CommandLineTestCase):
    def test_player_fifo_default(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "any-player.exe",
             "http://test.se", "test"],
            "any-player.exe \\\\.\\pipe\\streamlinkpipe",
        )

    def test_player_fifo_vlc(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "C:\\Program Files\\VideoLAN\\vlc.exe",
             "http://test.se", "test"],
            "C:\\Program Files\\VideoLAN\\vlc.exe --input-title-format http://test.se stream://\\\\\\.\\pipe\\streamlinkpipe",
        )

    def test_player_fifo_mpv(self):
        self._test_args(
            ["streamlink", "--player-fifo",
             "-p", "C:\\Program Files\\mpv\\mpv.exe",
             "http://test.se", "test"],
            "C:\\Program Files\\mpv\\mpv.exe --force-media-title=http://test.se file://\\\\.\\pipe\\streamlinkpipe",
        )
