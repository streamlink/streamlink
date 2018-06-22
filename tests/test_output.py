import ntpath
import posixpath
import unittest

from tests.mock import patch
from streamlink_cli.output import PlayerOutput


class TestPlayerOutput(unittest.TestCase):
    def test_supported_player_generic(self):
        self.assertEqual("vlc",
                         PlayerOutput.supported_player("vlc"))

        self.assertEqual("mpv",
                         PlayerOutput.supported_player("mpv"))

    @patch("streamlink_cli.output.os.path.basename", new=ntpath.basename)
    def test_supported_player_win32(self):
        self.assertEqual("mpv",
                         PlayerOutput.supported_player("C:\\MPV\\mpv.exe"))
        self.assertEqual("vlc",
                         PlayerOutput.supported_player("C:\\VLC\\vlc.exe"))

    @patch("streamlink_cli.output.os.path.basename", new=posixpath.basename)
    def test_supported_player_posix(self):
        self.assertEqual("mpv",
                         PlayerOutput.supported_player("/usr/bin/mpv"))
        self.assertEqual("vlc",
                         PlayerOutput.supported_player("/usr/bin/vlc"))

    @patch("streamlink_cli.output.os.path.basename", new=ntpath.basename)
    def test_supported_player_args_win32(self):
        self.assertEqual("mpv",
                         PlayerOutput.supported_player("C:\\MPV\\mpv.exe --argh"))
        self.assertEqual("vlc",
                         PlayerOutput.supported_player("C:\\VLC\\vlc.exe --argh"))

    @patch("streamlink_cli.output.os.path.basename", new=posixpath.basename)
    def test_supported_player_args_posix(self):
        self.assertEqual("mpv",
                         PlayerOutput.supported_player("/usr/bin/mpv --argh"))
        self.assertEqual("vlc",
                         PlayerOutput.supported_player("/usr/bin/vlc --argh"))

    @patch("streamlink_cli.output.os.path.basename", new=posixpath.basename)
    def test_supported_player_negative_posix(self):
        self.assertEqual(None,
                         PlayerOutput.supported_player("/usr/bin/xmpvideo"))
        self.assertEqual(None,
                         PlayerOutput.supported_player("/usr/bin/echo"))

    @patch("streamlink_cli.output.os.path.basename", new=ntpath.basename)
    def test_supported_player_negative_win32(self):
        self.assertEqual(None,
                         PlayerOutput.supported_player("C:\\mpc\\mpc-hd.exe"))
        self.assertEqual(None,
                         PlayerOutput.supported_player("C:\\mplayer\\not-vlc.exe"))
