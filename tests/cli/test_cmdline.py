import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, call, patch

import streamlink_cli.main
import tests
from streamlink import Streamlink


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
             patch("streamlink_cli.output.player.subprocess.Popen") as mock_popen, \
             patch("streamlink_cli.output.player.subprocess.call") as mock_call, \
             patch("streamlink_cli.output.player.which", side_effect=lambda path: path), \
             patch("streamlink_cli.output.player.sleep"):
            mock_argv.__getitem__.side_effect = lambda x: args[x]
            mock_popen.return_value = Mock(poll=Mock(side_effect=poll_factory([None, 0])))
            try:
                streamlink_cli.main.main()
            except SystemExit as exc:
                actual_exit_code = exc.code

        assert exit_code == actual_exit_code
        assert mock_setup_streamlink.call_count == 1
        if not passthrough:
            assert mock_popen.call_args_list == [call(commandline, bufsize=ANY, stdin=ANY, stdout=ANY, stderr=ANY)]
        else:
            assert mock_call.call_args_list == [call(commandline, stdout=ANY, stderr=ANY)]


class TestCommandLine(CommandLineTestCase):
    def test_open_regular_path_player(self):
        self._test_args(
            ["streamlink", "-p", "player", "http://test.se", "test"],
            ["player", "-"],
        )

    def test_open_player_extra_args_in_player(self):
        self._test_args(
            [
                "streamlink",
                "-p",
                "player",
                "-a",
                '''--input-title-format "Poker \\"Stars\\""''',
                "http://test.se",
                "test",
            ],
            [
                "player",
                "--input-title-format",
                "Poker \"Stars\"",
                "-",
            ],
        )

    def test_open_player_extra_args_in_player_pass_through(self):
        self._test_args(
            [
                "streamlink",
                "--player-passthrough",
                "hls",
                "-p",
                "player",
                "-a",
                '''--input-title-format "Poker \\"Stars\\""''',
                "test.se",
                "hls",
            ],
            [
                "player",
                "--input-title-format",
                "Poker \"Stars\"",
                "http://test.se/playlist.m3u8",
            ],
            passthrough=True,
        )

    def test_single_hyphen_extra_player_args_971(self):
        self._test_args(
            ["streamlink", "-p", "player", "-a", "-v {playerinput}", "http://test.se", "test"],
            ["player", "-v", "-"],
        )
