import datetime
import logging
import os
import sys
import unittest
from pathlib import Path, PosixPath, WindowsPath
from textwrap import dedent
from unittest.mock import Mock, call, patch

import freezegun
import pytest

import streamlink_cli.main
import tests.resources
from streamlink.exceptions import PluginError, StreamError
from streamlink.session import Streamlink
from streamlink.stream.stream import Stream
from streamlink_cli.compat import DeprecatedPath, stdout
from streamlink_cli.main import (
    Formatter,
    NoPluginError,
    check_file_output,
    create_output,
    format_valid_streams,
    handle_stream,
    handle_url,
    output_stream,
    resolve_stream_name,
    setup_config_args
)
from streamlink_cli.output import FileOutput, PlayerOutput
from tests import posix_only, windows_only
from tests.plugin.testplugin import TestPlugin as _TestPlugin


class FakePlugin(_TestPlugin):
    __module__ = "fake"
    _streams = {}  # type: ignore

    def streams(self, *args, **kwargs):
        return self._streams

    def _get_streams(self):  # pragma: no cover
        pass


class TestCLIMain(unittest.TestCase):
    def test_resolve_stream_name(self):
        a = Mock()
        b = Mock()
        c = Mock()
        d = Mock()
        e = Mock()
        streams = {
            "160p": a,
            "360p": b,
            "480p": c,
            "720p": d,
            "1080p": e,
            "worst": b,
            "best": d,
            "worst-unfiltered": a,
            "best-unfiltered": e
        }

        self.assertEqual(resolve_stream_name(streams, "unknown"), "unknown")
        self.assertEqual(resolve_stream_name(streams, "160p"), "160p")
        self.assertEqual(resolve_stream_name(streams, "360p"), "360p")
        self.assertEqual(resolve_stream_name(streams, "480p"), "480p")
        self.assertEqual(resolve_stream_name(streams, "720p"), "720p")
        self.assertEqual(resolve_stream_name(streams, "1080p"), "1080p")
        self.assertEqual(resolve_stream_name(streams, "worst"), "360p")
        self.assertEqual(resolve_stream_name(streams, "best"), "720p")
        self.assertEqual(resolve_stream_name(streams, "worst-unfiltered"), "160p")
        self.assertEqual(resolve_stream_name(streams, "best-unfiltered"), "1080p")

    def test_format_valid_streams(self):
        a = Mock()
        b = Mock()
        c = Mock()

        streams = {
            "audio": a,
            "720p": b,
            "1080p": c,
            "worst": b,
            "best": c
        }
        self.assertEqual(
            format_valid_streams(_TestPlugin, streams),
            ", ".join([
                "audio",
                "720p (worst)",
                "1080p (best)"
            ])
        )

        streams = {
            "audio": a,
            "720p": b,
            "1080p": c,
            "worst-unfiltered": b,
            "best-unfiltered": c
        }
        self.assertEqual(
            format_valid_streams(_TestPlugin, streams),
            ", ".join([
                "audio",
                "720p (worst-unfiltered)",
                "1080p (best-unfiltered)"
            ])
        )


class TestCLIMainHandleUrl:
    @pytest.mark.parametrize("side_effect,expected", [
        (NoPluginError("foo"), "No plugin can handle URL: fakeurl"),
        (PluginError("bar"), "bar"),
    ])
    def test_error(self, side_effect, expected):
        with patch("streamlink_cli.main.args", Mock(url="fakeurl")), \
             patch("streamlink_cli.main.streamlink", resolve_url=Mock(side_effect=side_effect)), \
             patch("streamlink_cli.main.console", exit=Mock(side_effect=SystemExit)) as mock_console:
            with pytest.raises(SystemExit):
                handle_url()
            assert mock_console.exit.mock_calls == [call(expected)]


class TestCLIMainJsonAndStreamUrl(unittest.TestCase):
    @patch("streamlink_cli.main.args", json=True, stream_url=True, subprocess_cmdline=False)
    @patch("streamlink_cli.main.console")
    def test_handle_stream_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(best=stream)

        plugin = FakePlugin(Mock(), "")
        plugin._streams = streams

        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [call(
            stream,
            metadata=dict(
                id="test-id-1234-5678",
                author="Tѥst Āuƭhǿr",
                category=None,
                title="Test Title"
            )
        )])
        self.assertEqual(console.error.mock_calls, [])
        console.msg_json.mock_calls.clear()

        args.json = False
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [call(stream.to_url())])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.error.mock_calls, [])
        console.msg.mock_calls.clear()

        stream.to_url.side_effect = TypeError()
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])

    @patch("streamlink_cli.main.args", json=True, stream_url=True, stream=[], default_stream=[], retry_max=0, retry_streams=0)
    @patch("streamlink_cli.main.console")
    def test_handle_url_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(worst=Mock(), best=stream)

        class _FakePlugin(FakePlugin):
            __module__ = FakePlugin.__module__
            _streams = streams

        with patch("streamlink_cli.main.streamlink", resolve_url=Mock(return_value=("fake", _FakePlugin, ""))):
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [call(
                plugin="fake",
                metadata=dict(
                    id="test-id-1234-5678",
                    author="Tѥst Āuƭhǿr",
                    category=None,
                    title="Test Title"
                ),
                streams=streams
            )])
            self.assertEqual(console.error.mock_calls, [])
            console.msg_json.mock_calls.clear()

            args.json = False
            handle_url()
            self.assertEqual(console.msg.mock_calls, [call(stream.to_manifest_url())])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.error.mock_calls, [])
            console.msg.mock_calls.clear()

            stream.to_manifest_url.side_effect = TypeError()
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])
            console.exit.mock_calls.clear()


class TestCLIMainCheckFileOutput(unittest.TestCase):
    @staticmethod
    def mock_path(path, is_file=True, resolve=""):
        return Mock(
            spec=Path(path),
            is_file=Mock(return_value=is_file),
            resolve=Mock(return_value=resolve),
            __str__=Mock(return_value=path)
        )

    @patch("streamlink_cli.main.log")
    def test_check_file_output(self, mock_log: Mock):
        path = self.mock_path("foo", is_file=False, resolve="/path/to/foo")
        output = check_file_output(path, False)
        self.assertIsInstance(output, FileOutput)
        self.assertIs(output.filename, path)
        self.assertEqual(mock_log.info.call_args_list, [call("Writing output to\n/path/to/foo")])
        self.assertEqual(mock_log.debug.call_args_list, [call("Checking file output")])

    def test_check_file_output_exists_force(self):
        path = self.mock_path("foo", is_file=True)
        output = check_file_output(path, True)
        self.assertIsInstance(output, FileOutput)
        self.assertIs(output.filename, path)

    @patch("streamlink_cli.main.console")
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_ask_yes(self, mock_sys: Mock, mock_console: Mock):
        mock_sys.stdin.isatty.return_value = True
        mock_console.ask = Mock(return_value="y")
        path = self.mock_path("foo", is_file=True)
        output = check_file_output(path, False)
        self.assertEqual(mock_console.ask.call_args_list, [call("File foo already exists! Overwrite it? [y/N] ")])
        self.assertIsInstance(output, FileOutput)
        self.assertIs(output.filename, path)

    @patch("streamlink_cli.main.console")
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_ask_no(self, mock_sys: Mock, mock_console: Mock):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.exit.side_effect = SystemExit
        mock_console.ask = Mock(return_value="N")
        path = self.mock_path("foo", is_file=True)
        with self.assertRaises(SystemExit):
            check_file_output(path, False)
        self.assertEqual(mock_console.ask.call_args_list, [call("File foo already exists! Overwrite it? [y/N] ")])

    @patch("streamlink_cli.main.console")
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_ask_error(self, mock_sys: Mock, mock_console: Mock):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.exit.side_effect = SystemExit
        mock_console.ask = Mock(return_value=None)
        path = self.mock_path("foo", is_file=True)
        with self.assertRaises(SystemExit):
            check_file_output(path, False)
        self.assertEqual(mock_console.ask.call_args_list, [call("File foo already exists! Overwrite it? [y/N] ")])

    @patch("streamlink_cli.main.console")
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_notty(self, mock_sys: Mock, mock_console: Mock):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.exit.side_effect = SystemExit
        path = self.mock_path("foo", is_file=True)
        with self.assertRaises(SystemExit):
            check_file_output(path, False)
        self.assertEqual(mock_console.ask.call_args_list, [])


class TestCLIMainCreateOutput(unittest.TestCase):
    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_no_file_output_options(self, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo"
        })
        args.output = None
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.player_fifo = False
        args.title = None
        args.url = "URL"
        args.player = "mpv"
        args.player_args = ""

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.title == "URL"

        args.title = "{author} - {title}"
        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.title == "foo - bar"

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_file_output(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = "foo"
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        assert mock_check_file_output.call_args_list == [call(Path("foo"), False)]
        assert type(output) is FileOutput
        assert output.filename == Path("foo")
        assert output.fd is None
        assert output.record is None

    @patch("streamlink_cli.main.args")
    def test_create_output_stdout(self, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record = None
        args.record_and_pipe = None

        output = create_output(formatter)
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert output.record is None

        args.output = "-"
        args.stdout = False
        output = create_output(formatter)
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert output.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_record_and_pipe(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = None
        args.stdout = None
        args.record_and_pipe = "foo"
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        assert mock_check_file_output.call_args_list == [call(Path("foo"), False)]
        assert type(output) is FileOutput
        assert output.filename is None
        assert output.fd is stdout
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record(self, mock_check_file_output: Mock, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo"
        })
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = None
        args.stdout = None
        args.record = "foo"
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None
        args.title = None
        args.url = "URL"
        args.player = "mpv"
        args.player_args = ""
        args.player_fifo = None
        args.player_http = None

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.title == "URL"
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

        args.title = "{author} - {title}"
        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.title == "foo - bar"
        assert type(output.record) is FileOutput
        assert output.record.filename == Path("foo")
        assert output.record.fd is None
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record_stdout(self, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo"
        })
        args.output = None
        args.stdout = None
        args.record = "-"
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None
        args.title = "{author} - {title}"
        args.url = "URL"
        args.player = "mpv"
        args.player_args = ""
        args.player_fifo = None
        args.player_http = None

        output = create_output(formatter)
        assert type(output) is PlayerOutput
        assert output.title == "foo - bar"
        assert type(output.record) is FileOutput
        assert output.record.filename is None
        assert output.record.fd is stdout
        assert output.record.record is None

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console")
    def test_create_output_record_and_other_file_output(self, console: Mock, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record_and_pipe = True
        create_output(formatter)
        console.exit.assert_called_with("Cannot use record options with other file output options.")

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console")
    def test_create_output_no_default_player(self, console: Mock, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = False
        args.record_and_pipe = False
        args.player = None
        console.exit.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            create_output(formatter)
        self.assertRegex(
            console.exit.call_args_list[0][0][0],
            r"^The default player \(\w+\) does not seem to be installed\."
        )


class TestCLIMainHandleStream(unittest.TestCase):
    @patch("streamlink_cli.main.output_stream")
    @patch("streamlink_cli.main.args")
    def test_handle_stream_output_stream(self, args: Mock, mock_output_stream: Mock):
        args.json = False
        args.subprocess_cmdline = False
        args.stream_url = False
        args.output = False
        args.stdout = False
        args.player_passthrough = []
        args.player_external_http = False
        args.player_continuous_http = False
        mock_output_stream.return_value = True

        session = Mock()
        plugin = FakePlugin(session, "")
        stream = Stream(session)
        streams = {"best": stream}

        handle_stream(plugin, streams, "best")
        self.assertEqual(mock_output_stream.call_count, 1)
        paramStream, paramFormatter = mock_output_stream.call_args[0]
        self.assertIs(paramStream, stream)
        self.assertIsInstance(paramFormatter, Formatter)


class TestCLIMainOutputStream(unittest.TestCase):
    @patch("streamlink_cli.main.args", Mock(retry_open=2))
    @patch("streamlink_cli.main.log")
    @patch("streamlink_cli.main.console")
    def test_stream_failure_no_output_open(self, mock_console: Mock, mock_log: Mock):
        output = Mock()
        stream = Mock(
            __str__=lambda _: "fake-stream",
            open=Mock(side_effect=StreamError("failure"))
        )
        formatter = Formatter({})

        with patch("streamlink_cli.main.output", Mock()), \
             patch("streamlink_cli.main.create_output", return_value=output):
            output_stream(stream, formatter)

        self.assertEqual(mock_log.error.call_args_list, [
            call("Try 1/2: Could not open stream fake-stream (Could not open stream: failure)"),
            call("Try 2/2: Could not open stream fake-stream (Could not open stream: failure)"),
        ])
        self.assertEqual(mock_console.exit.call_args_list, [
            call("Could not open stream fake-stream, tried 2 times, exiting")
        ])
        self.assertFalse(output.open.called, "Does not open the output on stream error")


@patch("streamlink_cli.main.log")
class TestCLIMainSetupConfigArgs(unittest.TestCase):
    configdir = Path(tests.resources.__path__[0], "cli", "config")
    parser = Mock()

    @classmethod
    def subject(cls, config_files, **args):
        def resolve_url(name):
            if name == "noplugin":
                raise NoPluginError()
            return name, Mock(__module__="testplugin"), name

        session = Mock()
        session.resolve_url.side_effect = resolve_url
        args.setdefault("url", "testplugin")

        with patch("streamlink_cli.main.setup_args") as mock_setup_args, \
             patch("streamlink_cli.main.args", **args), \
             patch("streamlink_cli.main.streamlink", session), \
             patch("streamlink_cli.main.CONFIG_FILES", config_files):
            setup_config_args(cls.parser)
            return mock_setup_args

    def test_no_plugin(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=None,
            url="noplugin"
        )
        expected = [self.configdir / "primary"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert not mock_log.warning.mock_calls

    def test_default_primary(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=None
        )
        expected = [self.configdir / "primary", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert not mock_log.warning.mock_calls

    def test_default_secondary_deprecated(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "non-existent", DeprecatedPath(self.configdir / "secondary")],
            config=None
        )
        expected = [self.configdir / "secondary", self.configdir / "secondary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert mock_log.warning.mock_calls == [
            call(f"Loaded config from deprecated path, see CLI docs for how to migrate: {expected[0]}"),
            call(f"Loaded plugin config from deprecated path, see CLI docs for how to migrate: {expected[1]}"),
        ]

    def test_custom_with_primary_plugin(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "custom")]
        )
        expected = [self.configdir / "custom", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert not mock_log.warning.mock_calls

    def test_custom_with_deprecated_plugin(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "non-existent", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "custom")]
        )
        expected = [self.configdir / "custom", DeprecatedPath(self.configdir / "secondary.testplugin")]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert mock_log.warning.mock_calls == [
            call(f"Loaded plugin config from deprecated path, see CLI docs for how to migrate: {expected[1]}"),
        ]

    def test_custom_multiple(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "non-existent"), str(self.configdir / "primary"), str(self.configdir / "secondary")]
        )
        expected = [self.configdir / "secondary", self.configdir / "primary", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        assert not mock_log.warning.mock_calls


class _TestCLIMainLogging(unittest.TestCase):
    # stop test execution at the setup_signals() call, as we're not interested in what comes afterwards
    class StopTest(Exception):
        pass

    @classmethod
    def subject(cls, argv, **kwargs):
        session = Streamlink()
        session.load_plugins(str(Path(tests.__path__[0]) / "plugin"))

        with patch("streamlink_cli.main.os.geteuid", create=True, new=Mock(return_value=kwargs.get("euid", 1000))), \
             patch("streamlink_cli.main.streamlink", session), \
             patch("streamlink_cli.main.setup_signals", side_effect=cls.StopTest), \
             patch("streamlink_cli.main.CONFIG_FILES", []), \
             patch("streamlink_cli.main.setup_streamlink"), \
             patch("streamlink_cli.main.setup_plugins"), \
             patch("streamlink_cli.main.setup_http_session"), \
             patch("streamlink.session.Streamlink.load_builtin_plugins"), \
             patch("sys.argv") as mock_argv:
            mock_argv.__getitem__.side_effect = lambda x: argv[x]
            try:
                streamlink_cli.main.main()
            except cls.StopTest:
                pass

    def tearDown(self):
        streamlink_cli.main.logger.root.handlers.clear()

    # python >=3.7.2: https://bugs.python.org/issue35046
    _write_call_log_cli_info = (
        [call("[cli][info] foo\n")]
        if sys.version_info >= (3, 7, 2) else
        [call("[cli][info] foo"), call("\n")]
    )
    _write_call_console_msg = [call("bar\n")]
    _write_call_console_msg_error = [call("error: bar\n")]
    _write_call_console_msg_json = [call("{\n  \"error\": \"bar\"\n}\n")]

    _write_calls = _write_call_log_cli_info + _write_call_console_msg

    def write_file_and_assert(self, mock_mkdir: Mock, mock_write: Mock, mock_stdout: Mock):
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(mock_mkdir.mock_calls, [call(parents=True, exist_ok=True)])
        self.assertEqual(mock_write.mock_calls, self._write_calls)
        self.assertFalse(mock_stdout.write.called)


class TestCLIMainLoggingStreams(_TestCLIMainLogging):
    # python >=3.7.2: https://bugs.python.org/issue35046
    _write_call_log_testcli_err = (
        [call("[test_cli_main][error] baz\n")]
        if sys.version_info >= (3, 7, 2) else
        [call("[test_cli_main][error] baz"), call("\n")]
    )

    def subject(self, argv, stream=None):
        super().subject(argv)
        childlogger = logging.getLogger("streamlink.test_cli_main")

        with self.assertRaises(SystemExit):
            streamlink_cli.main.log.info("foo")
            childlogger.error("baz")
            streamlink_cli.main.console.exit("bar")

        self.assertIs(streamlink_cli.main.log.parent.handlers[0].stream, stream)
        self.assertIs(childlogger.parent.handlers[0].stream, stream)
        self.assertIs(streamlink_cli.main.console.output, stream)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_stdout(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--stdout"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_output_eq_file(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--output=foo"], mock_stdout)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_output_eq_dash(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--output=-"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_eq_file(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--record=foo"], mock_stdout)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_eq_dash(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--record=-"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_and_pipe(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--record-and-pipe=foo"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_no_pipe_no_json(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink"], mock_stdout)
        self.assertEqual(mock_stdout.write.mock_calls,
                         self._write_call_log_cli_info + self._write_call_log_testcli_err + self._write_call_console_msg_error)
        self.assertEqual(mock_stderr.write.mock_calls, [])

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_no_pipe_json(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--json"], mock_stdout)
        self.assertEqual(mock_stdout.write.mock_calls, self._write_call_console_msg_json)
        self.assertEqual(mock_stderr.write.mock_calls, [])

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_pipe_no_json(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--stdout"], mock_stderr)
        self.assertEqual(mock_stdout.write.mock_calls, [])
        self.assertEqual(mock_stderr.write.mock_calls,
                         self._write_call_log_cli_info + self._write_call_log_testcli_err + self._write_call_console_msg_error)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_pipe_json(self, mock_stdout: Mock, mock_stderr: Mock):
        self.subject(["streamlink", "--stdout", "--json"], mock_stderr)
        self.assertEqual(mock_stdout.write.mock_calls, [])
        self.assertEqual(mock_stderr.write.mock_calls, self._write_call_console_msg_json)


class TestCLIMainLoggingInfos(_TestCLIMainLogging):
    @posix_only
    @patch("streamlink_cli.main.log")
    def test_log_root_warning(self, mock_log):
        self.subject(["streamlink"], euid=0)
        self.assertEqual(mock_log.info.mock_calls, [call("streamlink is running as root! Be careful!")])

    @patch("streamlink_cli.main.log")
    @patch("streamlink_cli.main.streamlink_version", "streamlink")
    @patch("streamlink_cli.main.importlib_metadata")
    @patch("streamlink_cli.main.log_current_arguments", Mock(side_effect=_TestCLIMainLogging.StopTest))
    @patch("platform.python_version", Mock(return_value="python"))
    def test_log_current_versions(self, mock_importlib_metadata: Mock, mock_log: Mock):
        class FakePackageNotFoundError(Exception):
            pass

        def version(dist):
            if dist == "foo":
                return "1.2.3"
            if dist == "bar-baz":
                return "2.0.0"
            raise FakePackageNotFoundError()

        mock_importlib_metadata.PackageNotFoundError = FakePackageNotFoundError
        mock_importlib_metadata.requires.return_value = ["foo>1", "bar-baz==2", "qux~=3"]
        mock_importlib_metadata.version.side_effect = version

        self.subject(["streamlink", "--loglevel", "info"])
        self.assertEqual(mock_log.debug.mock_calls, [], "Doesn't log anything if not debug logging")

        with patch("sys.platform", "linux"), \
             patch("platform.platform", Mock(return_value="linux")):
            self.subject(["streamlink", "--loglevel", "debug"])
            assert mock_importlib_metadata.requires.mock_calls == [call("streamlink")]
            assert mock_log.debug.mock_calls == [
                call("OS:         linux"),
                call("Python:     python"),
                call("Streamlink: streamlink"),
                call("Dependencies:"),
                call(" foo: 1.2.3"),
                call(" bar-baz: 2.0.0"),
            ]
            mock_importlib_metadata.requires.reset_mock()
            mock_log.debug.reset_mock()

        with patch("sys.platform", "darwin"), \
             patch("platform.mac_ver", Mock(return_value=["0.0.0"])):
            self.subject(["streamlink", "--loglevel", "debug"])
            assert mock_importlib_metadata.requires.mock_calls == [call("streamlink")]
            assert mock_log.debug.mock_calls == [
                call("OS:         macOS 0.0.0"),
                call("Python:     python"),
                call("Streamlink: streamlink"),
                call("Dependencies:"),
                call(" foo: 1.2.3"),
                call(" bar-baz: 2.0.0"),
            ]
            mock_importlib_metadata.requires.reset_mock()
            mock_log.debug.reset_mock()

        with patch("sys.platform", "win32"), \
             patch("platform.system", Mock(return_value="Windows")), \
             patch("platform.release", Mock(return_value="0.0.0")):
            self.subject(["streamlink", "--loglevel", "debug"])
            assert mock_importlib_metadata.requires.mock_calls == [call("streamlink")]
            assert mock_log.debug.mock_calls == [
                call("OS:         Windows 0.0.0"),
                call("Python:     python"),
                call("Streamlink: streamlink"),
                call("Dependencies:"),
                call(" foo: 1.2.3"),
                call(" bar-baz: 2.0.0"),
            ]
            mock_importlib_metadata.requires.reset_mock()
            mock_log.debug.reset_mock()

    @patch("streamlink_cli.main.log")
    def test_log_current_arguments(self, mock_log):
        self.subject([
            "streamlink",
            "--loglevel", "info"
        ])
        self.assertEqual(mock_log.debug.mock_calls, [], "Doesn't log anything if not debug logging")

        self.subject([
            "streamlink",
            "--loglevel", "debug",
            "-p", "custom",
            "--testplugin-bool",
            "--testplugin-password=secret",
            "test.se/channel",
            "best,worst"
        ])
        self.assertEqual(
            mock_log.debug.mock_calls[-7:],
            [
                call("Arguments:"),
                call(" url=test.se/channel"),
                call(" stream=['best', 'worst']"),
                call(" --loglevel=debug"),
                call(" --player=custom"),
                call(" --testplugin-bool=True"),
                call(" --testplugin-password=********")
            ]
        )


class TestCLIMainLoggingLogfile(_TestCLIMainLogging):
    @patch("sys.stdout")
    @patch("builtins.open")
    def test_logfile_no_logfile(self, mock_open, mock_stdout):
        self.subject(["streamlink"])
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(streamlink_cli.main.console.output, sys.stdout)
        self.assertFalse(mock_open.called)
        self.assertEqual(mock_stdout.write.mock_calls, self._write_calls)

    @patch("sys.stdout")
    @patch("builtins.open")
    def test_logfile_loglevel_none(self, mock_open, mock_stdout):
        self.subject(["streamlink", "--loglevel", "none", "--logfile", "foo"])
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(streamlink_cli.main.console.output, sys.stdout)
        self.assertFalse(mock_open.called)
        self.assertEqual(mock_stdout.write.mock_calls, [call("bar\n")])

    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    def test_logfile_path_relative(self, mock_open, mock_stdout):
        path = Path("foo").resolve()
        self.subject(["streamlink", "--logfile", "foo"])
        self.write_file_and_assert(
            mock_mkdir=path.mkdir,
            mock_write=mock_open(str(path), "a").write,
            mock_stdout=mock_stdout
        )


@posix_only
class TestCLIMainLoggingLogfilePosix(_TestCLIMainLogging):
    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    def test_logfile_path_absolute(self, mock_open, mock_stdout):
        self.subject(["streamlink", "--logfile", "/foo/bar"])
        self.write_file_and_assert(
            mock_mkdir=PosixPath("/foo").mkdir,
            mock_write=mock_open("/foo/bar", "a").write,
            mock_stdout=mock_stdout
        )

    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    def test_logfile_path_expanduser(self, mock_open, mock_stdout):
        with patch.dict(os.environ, {"HOME": "/foo"}):
            self.subject(["streamlink", "--logfile", "~/bar"])
        self.write_file_and_assert(
            mock_mkdir=PosixPath("/foo").mkdir,
            mock_write=mock_open("/foo/bar", "a").write,
            mock_stdout=mock_stdout
        )

    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    @freezegun.freeze_time(datetime.datetime(2000, 1, 2, 3, 4, 5))
    def test_logfile_path_auto(self, mock_open, mock_stdout):
        with patch("streamlink_cli.constants.LOG_DIR", PosixPath("/foo")):
            self.subject(["streamlink", "--logfile", "-"])
        self.write_file_and_assert(
            mock_mkdir=PosixPath("/foo").mkdir,
            mock_write=mock_open("/foo/2000-01-02_03-04-05.log", "a").write,
            mock_stdout=mock_stdout
        )


@windows_only
class TestCLIMainLoggingLogfileWindows(_TestCLIMainLogging):
    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    def test_logfile_path_absolute(self, mock_open, mock_stdout):
        self.subject(["streamlink", "--logfile", "C:\\foo\\bar"])
        self.write_file_and_assert(
            mock_mkdir=WindowsPath("C:\\foo").mkdir,
            mock_write=mock_open("C:\\foo\\bar", "a").write,
            mock_stdout=mock_stdout
        )

    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    def test_logfile_path_expanduser(self, mock_open, mock_stdout):
        with patch.dict(os.environ, {"USERPROFILE": "C:\\foo"}):
            self.subject(["streamlink", "--logfile", "~\\bar"])
        self.write_file_and_assert(
            mock_mkdir=WindowsPath("C:\\foo").mkdir,
            mock_write=mock_open("C:\\foo\\bar", "a").write,
            mock_stdout=mock_stdout
        )

    @patch("sys.stdout")
    @patch("builtins.open")
    @patch("pathlib.Path.mkdir", Mock())
    @freezegun.freeze_time(datetime.datetime(2000, 1, 2, 3, 4, 5))
    def test_logfile_path_auto(self, mock_open, mock_stdout):
        with patch("streamlink_cli.constants.LOG_DIR", WindowsPath("C:\\foo")):
            self.subject(["streamlink", "--logfile", "-"])
        self.write_file_and_assert(
            mock_mkdir=WindowsPath("C:\\foo").mkdir,
            mock_write=mock_open("C:\\foo\\2000-01-02_03-04-05.log", "a").write,
            mock_stdout=mock_stdout
        )


class TestCLIMainPrint(unittest.TestCase):
    def subject(self):
        with patch.object(Streamlink, "load_builtin_plugins"), \
             patch.object(Streamlink, "resolve_url") as mock_resolve_url, \
             patch.object(Streamlink, "resolve_url_no_redirect") as mock_resolve_url_no_redirect:
            session = Streamlink()
            session.load_plugins(str(Path(tests.__path__[0]) / "plugin"))
            with patch("streamlink_cli.main.os.geteuid", create=True, new=Mock(return_value=1000)), \
                 patch("streamlink_cli.main.streamlink", session), \
                 patch("streamlink_cli.main.CONFIG_FILES", []), \
                 patch("streamlink_cli.main.setup_streamlink"), \
                 patch("streamlink_cli.main.setup_plugins"), \
                 patch("streamlink_cli.main.setup_http_session"), \
                 patch("streamlink_cli.main.setup_signals"), \
                 patch("streamlink_cli.main.setup_options") as mock_setup_options:
                with self.assertRaises(SystemExit) as cm:
                    streamlink_cli.main.main()
                self.assertEqual(cm.exception.code, 0)
                mock_resolve_url.assert_not_called()
                mock_resolve_url_no_redirect.assert_not_called()
                mock_setup_options.assert_not_called()

    @staticmethod
    def get_stdout(mock_stdout):
        return "".join([call_arg[0][0] for call_arg in mock_stdout.write.call_args_list])

    @patch("sys.stdout")
    @patch("sys.argv", ["streamlink"])
    def test_print_usage(self, mock_stdout):
        self.subject()
        self.assertEqual(
            self.get_stdout(mock_stdout),
            "usage: streamlink [OPTIONS] <URL> [STREAM]\n\n"
            + "Use -h/--help to see the available options or read the manual at https://streamlink.github.io\n"
        )

    @patch("sys.stdout")
    @patch("sys.argv", ["streamlink", "--help"])
    def test_print_help(self, mock_stdout):
        self.subject()
        output = self.get_stdout(mock_stdout)
        self.assertIn(
            "usage: streamlink [OPTIONS] <URL> [STREAM]",
            output
        )
        self.assertIn(
            dedent("""
                Streamlink is a command-line utility that extracts streams from various
                services and pipes them into a video player of choice.
            """),
            output
        )
        self.assertIn(
            dedent("""
                For more in-depth documentation see:
                  https://streamlink.github.io

                Please report broken plugins or bugs to the issue tracker on Github:
                  https://github.com/streamlink/streamlink/issues
            """),
            output
        )

    @patch("sys.stdout")
    @patch("sys.argv", ["streamlink", "--plugins"])
    def test_print_plugins(self, mock_stdout):
        self.subject()
        self.assertEqual(self.get_stdout(mock_stdout), "Loaded plugins: testplugin\n")

    @patch("sys.stdout")
    @patch("sys.argv", ["streamlink", "--plugins", "--json"])
    def test_print_plugins_json(self, mock_stdout):
        self.subject()
        self.assertEqual(self.get_stdout(mock_stdout), """[\n  "testplugin"\n]\n""")
