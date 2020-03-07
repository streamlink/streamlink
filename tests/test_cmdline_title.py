# -*- coding: utf-8 -*-
import unittest

from streamlink.compat import is_win32, is_py3
from streamlink.utils import get_filesystem_encoding
from tests.test_cmdline import CommandLineTestCase


@unittest.skipIf(is_win32, "test only applicable in a POSIX OS")
class TestCommandLineWithTitlePOSIX(CommandLineTestCase):
    def test_open_player_with_title_vlc(self):
        self._test_args(["streamlink", "-p", "/usr/bin/vlc", "--title", "{title}", "http://test.se", "test"],
                        ["/usr/bin/vlc", "--input-title-format", 'Test Title', "-"])

    def test_open_player_with_unicode_author_vlc(self):
        self._test_args(["streamlink", "-p", "/usr/bin/vlc", "--title", "{author}", "http://test.se", "test"],
                        ["/usr/bin/vlc", "--input-title-format", u"Tѥst Āuƭhǿr", "-"])

    def test_open_player_with_default_title_vlc(self):
        self._test_args(["streamlink", "-p", "/usr/bin/vlc", "http://test.se", "test"],
                        ["/usr/bin/vlc", "--input-title-format", 'http://test.se', "-"])

    def test_open_player_with_default_title_vlc_args(self):
        self._test_args(["streamlink", "-p", "\"/Applications/VLC/vlc\" --other-option", "http://test.se", "test"],
                        ["/Applications/VLC/vlc", "--other-option", "--input-title-format", 'http://test.se', "-"])

    def test_open_player_with_title_mpv(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "{title}", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title=Test Title", "-"])


@unittest.skipIf(not is_win32, "test only applicable on Windows")
class TestCommandLineWithTitleWindows(CommandLineTestCase):
    def test_open_player_with_title_vlc(self):
        self._test_args(
            ["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe",
             "--title", "{title}", "http://test.se", "test"],
            "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \"Test Title\" -"
        )

    @unittest.skipIf(is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_vlc_py2(self):
        self._test_args(
            ["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe",
             "--title", "{author}", "http://test.se", "test"],
            "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \""
            + u"Tѥst Āuƭhǿr".encode(get_filesystem_encoding())
            + "\" -"
        )

    @unittest.skipIf(not is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_vlc_py3(self):
        self._test_args(
            ["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe",
             "--title", "{author}", "http://test.se", "test"],
            u"c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \"Tѥst Āuƭhǿr\" -"
        )

    def test_open_player_with_default_title_vlc(self):
        self._test_args(
            ["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe", "http://test.se", "test"],
            "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format http://test.se -"
        )

    def test_open_player_with_default_arg_vlc(self):
        self._test_args(
            ["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe --argh", "http://test.se", "test"],
            "c:\\Program Files\\VideoLAN\\vlc.exe --argh --input-title-format http://test.se -"
        )

    # PotPlayer
    def test_open_player_with_title_pot(self):
        self._test_args(
            ["streamlink", "-p", "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\"",
             "--title", "{title}", "http://test.se/stream", "hls", "--player-passthrough", "hls"],
            "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\" \"http://test.se/playlist.m3u8\\Test Title\"",
            passthrough=True
        )

    @unittest.skipIf(is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_pot_py2(self):
        self._test_args(
            ["streamlink", "-p", "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\"",
             "--title", "{author}", "http://test.se/stream", "hls", "--player-passthrough", "hls"],
            "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\" \"http://test.se/playlist.m3u8\\"
            + u"Tѥst Āuƭhǿr".encode(get_filesystem_encoding())
            + "\"",
            passthrough=True
        )

    @unittest.skipIf(not is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_pot_py3(self):
        self._test_args(
            ["streamlink", "-p", "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\"",
             "--title", "{author}", "http://test.se/stream", "hls", "--player-passthrough", "hls"],
            u"\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\" "
            + u"\"http://test.se/playlist.m3u8\\Tѥst Āuƭhǿr\"",
            passthrough=True
        )

    def test_open_player_with_default_title_pot(self):
        self._test_args(
            ["streamlink", "-p", "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\"",
             "http://test.se/stream", "hls", "--player-passthrough", "hls"],
            "\"c:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe\" "
            + "\"http://test.se/playlist.m3u8\\http://test.se/stream\"",
            passthrough=True
        )
