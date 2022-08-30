import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import streamlink_cli.main
import tests
from streamlink import Streamlink
from tests import posix_only, windows_only


class CommandLineTestCase(unittest.TestCase):
    """
    Test that when invoked for the command line arguments are parsed as expected
    """

    @patch('streamlink_cli.main.CONFIG_FILES', [])
    @patch('streamlink_cli.main.setup_streamlink')
    @patch('streamlink_cli.main.setup_logger_and_console', Mock())
    @patch('streamlink_cli.output.sleep')
    @patch('streamlink_cli.output.subprocess.call')
    @patch('streamlink_cli.output.subprocess.Popen')
    @patch('sys.argv')
    def _test_args(self, args, commandline, mock_argv, mock_popen, mock_call, mock_sleep, mock_setup_streamlink,
                   passthrough=False, exit_code=0):
        mock_argv.__getitem__.side_effect = lambda x: args[x]

        def side_effect(results):
            def fn(*args):
                result = results.pop(0)
                return result

            return fn

        mock_popen.return_value = Mock(poll=Mock(side_effect=side_effect([None, 0])))

        session = Streamlink()
        session.load_plugins(str(Path(tests.__path__[0]) / "plugin"))

        actual_exit_code = 0
        with patch('streamlink_cli.main.streamlink', session):
            try:
                streamlink_cli.main.main()
            except SystemExit as exc:
                actual_exit_code = exc.code

        self.assertEqual(exit_code, actual_exit_code)
        mock_setup_streamlink.assert_called_with()
        if not passthrough:
            mock_popen.assert_called_with(commandline, stderr=ANY, stdout=ANY, bufsize=ANY, stdin=ANY)
        else:
            mock_call.assert_called_with(commandline, stderr=ANY, stdout=ANY)


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
                         "-a", '''--input-title-format "Poker \\"Stars\\"" {filename}''',
                         "http://test.se", "test"],
                        ["/usr/bin/player", "--input-title-format", 'Poker "Stars"', "-"])

    def test_open_player_extra_args_in_player_pass_through(self):
        self._test_args(["streamlink", "--player-passthrough", "hls", "-p", "/usr/bin/player",
                         "-a", '''--input-title-format "Poker \\"Stars\\"" {filename}''',
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
                        '''c:\\Program Files\\Player\\player.exe --input-title-format "Poker \\"Stars\\"" -''')

    def test_open_player_extra_args_in_player(self):
        self._test_args(["streamlink", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", '''--input-title-format "Poker \\"Stars\\"" {filename}''',
                         "http://test.se", "test"],
                        '''c:\\Program Files\\Player\\player.exe --input-title-format "Poker \\"Stars\\"" -''')

    def test_open_player_extra_args_in_player_pass_through(self):
        self._test_args(["streamlink", "--player-passthrough", "hls", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", '''--input-title-format "Poker \\"Stars\\"" {filename}''',
                         "test.se", "hls"],
                        '''c:\\Program Files\\Player\\player.exe'''
                        + ''' --input-title-format "Poker \\"Stars\\"" \"http://test.se/playlist.m3u8\"''',
                        passthrough=True)

    def test_single_hyphen_extra_player_args_971(self):
        """single hyphen params at the beginning of --player-args
           - https://github.com/streamlink/streamlink/issues/971 """
        self._test_args(["streamlink", "-p", "c:\\Program Files\\Player\\player.exe",
                         "-a", "-v {filename}", "http://test.se", "test"],
                        "c:\\Program Files\\Player\\player.exe -v -")
