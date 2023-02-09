import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, call, patch

import streamlink_cli.main
import tests
from streamlink import Streamlink
from tests import posix_only, windows_only


class CommandLineTestCase(unittest.TestCase):
    """
    Test that when invoked for the command line arguments are parsed as expected
    """

    @staticmethod
    def _test_args(args, commandline, passthrough=False, exit_code=0):
        def poll_factory(results):
            def fn(*_):
                result = results.pop(0)
                return result

            return fn

        with patch("streamlink.session.Streamlink.load_builtin_plugins"):
            session = Streamlink()
        session.load_plugins(str(Path(tests.__path__[0]) / "plugin"))

        actual_exit_code = 0
        with patch("sys.argv") as mock_argv, \
             patch("streamlink_cli.main.CONFIG_FILES", []), \
             patch("streamlink_cli.main.setup_logger_and_console"), \
             patch("streamlink_cli.main.setup_plugins"), \
             patch("streamlink_cli.main.setup_streamlink") as mock_setup_streamlink, \
             patch("streamlink_cli.main.streamlink", session), \
             patch("streamlink_cli.output.subprocess.Popen") as mock_popen, \
             patch("streamlink_cli.output.subprocess.call") as mock_call, \
             patch("streamlink_cli.output.sleep"):
            mock_argv.__getitem__.side_effect = lambda x: args[x]
            mock_popen.return_value = Mock(poll=Mock(side_effect=poll_factory([None, 0])))
            try:
                streamlink_cli.main.main()
            except SystemExit as exc:
                actual_exit_code = exc.code

        assert exit_code == actual_exit_code
        assert mock_setup_streamlink.call_count == 1
        if not passthrough:
            assert mock_popen.call_args_list == [call(commandline, stderr=ANY, stdout=ANY, bufsize=ANY, stdin=ANY)]
        else:
            assert mock_call.call_args_list == [call(commandline, stderr=ANY, stdout=ANY)]


@posix_only
class TestCommandLinePOSIX(CommandLineTestCase):
    """
    Commandline tests under POSIX-like operating systems
    """

    def test_open_regular_path_player(self):
        self._test_args(["streamlink", "-p", "/usr/bin/player", "http://test.se", "test"],
                        ["/usr/bin/player", "-"])

    def test_open_space_path_player(self):
        self._test_args(["streamlink", "-p", "\"/Applications/Video Player/player\"", "http://test.se", "test"],
                        ["/Applications/Video Player/player", "-"])
        # escaped
        self._test_args(["streamlink", "-p", "/Applications/Video\\ Player/player", "http://test.se", "test"],
                        ["/Applications/Video Player/player", "-"])

    def test_open_player_extra_args_in_player(self):
        self._test_args(["streamlink", "-p", "/usr/bin/player",
                         "-a", """--input-title-format "Poker \\"Stars\\"" {filename}""",
                         "http://test.se", "test"],
                        ["/usr/bin/player", "--input-title-format", 'Poker "Stars"', "-"])

    def test_open_player_extra_args_in_player_pass_through(self):
        self._test_args(["streamlink", "--player-passthrough", "hls", "-p", "/usr/bin/player",
                         "-a", """--input-title-format "Poker \\"Stars\\"" {filename}""",
                         "test.se", "hls"],
                        ["/usr/bin/player", "--input-title-format", 'Poker "Stars"', "http://test.se/playlist.m3u8"],
                        passthrough=True)

    def test_single_hyphen_extra_player_args_971(self):
        """single hyphen params at the beginning of --player-args
           - https://github.com/streamlink/streamlink/issues/971 """
        self._test_args(["streamlink", "-p", "/usr/bin/player", "-a", "-v {filename}",
                         "http://test.se", "test"],
                        ["/usr/bin/player", "-v", "-"])


@windows_only
class TestCommandLineWindows(CommandLineTestCase):
    """
    Commandline tests for Windows
    """

    def test_open_space_path_player(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\Player\\player.exe", "http://test.se", "test"],
                        "c:\\Program Files\\Player\\player.exe -")

    def test_open_space_quote_path_player(self):
        self._test_args(["streamlink", "-p", "\"c:\\Program Files\\Player\\player.exe\"", "http://test.se", "test"],
                        "\"c:\\Program Files\\Player\\player.exe\" -")

    def test_open_player_args_with_quote_in_player(self):
        self._test_args(["streamlink", "-p",
                         '''c:\\Program Files\\Player\\player.exe --input-title-format "Poker \\"Stars\\""''',
                         "http://test.se", "test"],
                        """c:\\Program Files\\Player\\player.exe --input-title-format "Poker \\"Stars\\"" -""")

    def test_open_player_extra_args_in_player(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", """--input-title-format "Poker \\"Stars\\"" {filename}""",
                         "http://test.se", "test"],
                        """c:\\Program Files\\Player\\player.exe --input-title-format "Poker \\"Stars\\"" -""")

    def test_open_player_extra_args_in_player_pass_through(self):
        self._test_args(["streamlink", "--player-passthrough", "hls", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", """--input-title-format "Poker \\"Stars\\"" {filename}""",
                         "test.se", "hls"],
                        """c:\\Program Files\\Player\\player.exe"""
                        + ''' --input-title-format "Poker \\"Stars\\"" \"http://test.se/playlist.m3u8\"''',
                        passthrough=True)

    def test_single_hyphen_extra_player_args_971(self):
        """single hyphen params at the beginning of --player-args
           - https://github.com/streamlink/streamlink/issues/971 """
        self._test_args(["streamlink", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", "-v {filename}", "http://test.se", "test"],
                        "c:\\Program Files\\Player\\player.exe -v -")
