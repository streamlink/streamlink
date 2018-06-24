# coding=utf8
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
                        ["/usr/bin/mpv", "--title", 'Test Title', "-"])

    def test_open_player_with_title_mpv_escape_1(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "no escape $$ codes $", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'no escape $$$$ codes $$', "-"])

    def test_open_player_with_title_mpv_escape_2(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "\$> begins with escape code $$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", '$> begins with escape code $$', "-"])

    def test_open_player_with_title_mpv_escape_3(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "ends with escape code $$ \$>", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'ends with escape code $$$$ $>', "-"])

    def test_open_player_with_title_mpv_escape_4(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "\$> $$ begins with escape and double \$> $$ escape codes", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", '$> $$ begins with escape and double $> $$ escape codes', "-"])

    def test_open_player_with_title_mpv_escape_5(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", r'\$> \\$> showing "\$>" after escaping', "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", r'$> \$> showing "$>" after escaping', "-"])

    def test_open_player_with_title_mpv_escape_6(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "$$$$$$> not a valid way to escape $", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", '$$$$$$$$$$$$> not a valid way to escape $$', "-"])

    def test_open_player_with_title_mpv_escape_7(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "$> also not a valid way to escape $", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", '$$> also not a valid way to escape $$', "-"])

    def test_open_player_with_title_mpv_escape_8(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "not valid $$$$$$> not a valid way to escape $", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'not valid $$$$$$$$$$$$> not a valid way to escape $$', "-"])

    def test_open_player_with_title_mpv_escape_9(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "Multiple $> \$> $> $$ \$> $$> $> \$> $> $> \$> \$> \$>\$>$$$$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'Multiple $$> $> $> $$ $> $$> $> $> $> $> $> $> $>$>$$$$', "-"])

    def test_open_player_with_title_mpv_escape_10(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "odd leading $$$\$> $$$ $>", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'odd leading $$$$$$$> $$$ $>', "-"])

    def test_open_player_with_title_mpv_escape_11(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "even leading $$\$\$> $$$$$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'even leading $$$$$$> $$$$$$$$$$', "-"]) #will expand after \$> because even number of $

    def test_open_player_with_title_mpv_escape_12(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", r"$$$$$\$\$> even leading beginning $$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", r'$$$$$$$$$$$$> even leading beginning $$$$', "-"])

    def test_open_player_with_title_mpv_escape_13(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", r"$$$$$\$> odd leading beginning $$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", r'$$$$$$$$$$$> odd leading beginning $$', "-"])

    def test_open_player_with_title_mpv_escape_14(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "odd and even $\$> $$ \$\$> $$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'odd and even $$$> $$ $$> $$', "-"])

    def test_open_player_with_title_mpv_escape_15(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", "even and odd \$\$> $$ $\$> $$", "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", 'even and odd $$> $$$$ $$$> $$', "-"])

    def test_open_player_with_title_mpv_escape_16(self):
        self._test_args(["streamlink", "-p", "/usr/bin/mpv", "--title", r'\$\$> $$$ \\$> $ showing "\$>" before escaping', "http://test.se", "test"],
                        ["/usr/bin/mpv", "--title", r'$$> $$$$$$ \$> $ showing "$>" before escaping', "-"])

@unittest.skipIf(not is_win32, "test only applicable on Windows")
class TestCommandLineWithTitleWindows(CommandLineTestCase):
    def test_open_player_with_title_vlc(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe", "--title", "{title}", "http://test.se", "test"],
                        "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \"Test Title\" -")

    @unittest.skipIf(is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_vlc_py2(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe", "--title", "{author}", "http://test.se", "test"],
                        "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \"" + u"Tѥst Āuƭhǿr".encode(get_filesystem_encoding()) + "\" -")

    @unittest.skipIf(not is_py3, "Encoding is different in Python 2")
    def test_open_player_with_unicode_author_vlc_py3(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe", "--title", "{author}", "http://test.se", "test"],
                        u"c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format \"Tѥst Āuƭhǿr\" -")

    def test_open_player_with_default_title_vlc(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe", "http://test.se", "test"],
                        "c:\\Program Files\\VideoLAN\\vlc.exe --input-title-format http://test.se -")

    def test_open_player_with_default_arg_vlc(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\VideoLAN\\vlc.exe --argh", "http://test.se", "test"],
                        "c:\\Program Files\\VideoLAN\\vlc.exe --argh --input-title-format http://test.se -")
