# -*- coding: utf-8 -*-

import logging
import os
import sys
import tempfile
import unittest
from textwrap import dedent

import streamlink_cli.main
from streamlink.exceptions import StreamError
from streamlink.session import Streamlink
from streamlink_cli.compat import is_py2, is_win32, stdout
from streamlink_cli.main import (
    Formatter,
    check_file_output,
    create_output,
    format_valid_streams,
    handle_stream,
    handle_url,
    output_stream,
    resolve_stream_name,
)
from streamlink_cli.output import FileOutput, PlayerOutput
from tests.mock import Mock, call, patch
from tests.plugins.testplugin import TestPlugin as _TestPlugin


class FakePlugin(_TestPlugin):
    module = "fake"
    arguments = []
    _streams = {}

    def streams(self, *args, **kwargs):
        return self._streams

    def _get_streams(self):  # pragma: no cover
        pass


class TestCLIMain(unittest.TestCase):
    @patch("streamlink_cli.main.log")
    def test_check_file_output(self, mock_log):
        streamlink_cli.main.console = Mock()
        self.assertIsInstance(check_file_output("foo", False), FileOutput)
        self.assertEqual(mock_log.debug.call_args_list, [call("Checking file output")])

    def test_check_file_output_exists(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            streamlink_cli.main.sys.stdin = stdin = Mock()
            stdin.isatty.return_value = True
            console.ask.return_value = "y"
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, False), FileOutput)
        finally:
            tmpfile.close()

    def test_check_file_output_exists_notty(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            streamlink_cli.main.sys.stdin = stdin = Mock()
            stdin.isatty.return_value = False
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertRaises(SystemExit, check_file_output, tmpfile.name, False)
        finally:
            tmpfile.close()

    def test_check_file_output_exists_force(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, True), FileOutput)
        finally:
            tmpfile.close()

    @patch('sys.exit')
    def test_check_file_output_exists_no(self, sys_exit):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            console.ask.return_value = "n"
            self.assertTrue(os.path.exists(tmpfile.name))
            check_file_output(tmpfile.name, False)
            sys_exit.assert_called_with()
        finally:
            tmpfile.close()

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

    @patch("streamlink_cli.main.args", json=True, stream_url=True, subprocess_cmdline=False)
    @patch("streamlink_cli.main.console", json=True)
    def test_handle_stream_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(best=stream)

        plugin = FakePlugin("")
        plugin._streams = streams

        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [call(
            stream,
            metadata=dict(
                id=u"test-id-1234-5678",
                author=u"Tѥst Āuƭhǿr",
                category=None,
                title=u"Test Title"
            )
        )])
        self.assertEqual(console.error.mock_calls, [])
        console.msg_json.mock_calls *= 0

        console.json = False
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [call("{0}", stream.to_url())])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.error.mock_calls, [])
        console.msg.mock_calls *= 0

        stream.to_url.side_effect = TypeError()
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])

    @patch("streamlink_cli.main.args", json=True, stream_url=True, stream=[], default_stream=[], retry_max=0, retry_streams=0)
    @patch("streamlink_cli.main.console", json=True)
    def test_handle_url_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(worst=Mock(), best=stream)

        class _FakePlugin(FakePlugin):
            _streams = streams

        with patch("streamlink_cli.main.streamlink", resolve_url=Mock(return_value=(_FakePlugin, ""))):
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [call(
                plugin="fake",
                metadata=dict(
                    id=u"test-id-1234-5678",
                    author=u"Tѥst Āuƭhǿr",
                    category=None,
                    title=u"Test Title"
                ),
                streams=streams
            )])
            self.assertEqual(console.error.mock_calls, [])
            console.msg_json.mock_calls *= 0

            console.json = False
            handle_url()
            self.assertEqual(console.msg.mock_calls, [call("{0}", stream.to_manifest_url())])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.error.mock_calls, [])
            console.msg.mock_calls *= 0

            stream.to_manifest_url.side_effect = TypeError()
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])
            console.exit.mock_calls *= 0

    def test_create_output_no_file_output_options(self):
        streamlink_cli.main.console = Mock()
        streamlink_cli.main.args = args = Mock()
        args.output = None
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.player_fifo = False
        args.title = None
        args.player = "mpv"
        args.player_args = ""
        self.assertIsInstance(create_output(FakePlugin), PlayerOutput)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_file_output(self, mock_check_file_output, args):
        # type: (Mock, Mock)
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        formatter = Formatter({})
        args.output = "foo"
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        self.assertEqual(mock_check_file_output.call_args_list, [call("foo", False)])
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, "foo")
        self.assertIsNone(output.fd)
        self.assertIsNone(output.record)

    def test_create_output_stdout(self):
        streamlink_cli.main.console = Mock()
        streamlink_cli.main.args = args = Mock()
        args.output = None
        args.stdout = True
        self.assertIsInstance(create_output(FakePlugin), FileOutput)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    def test_create_output_record_and_pipe(self, mock_check_file_output, args):
        # type: (Mock, Mock)
        formatter = Formatter({})
        mock_check_file_output.side_effect = lambda path, force: FileOutput(path)
        args.output = None
        args.stdout = None
        args.record_and_pipe = "foo"
        args.force = False
        args.fs_safe_rules = None

        output = create_output(formatter)
        self.assertEqual(mock_check_file_output.call_args_list, [call("foo", False)])
        self.assertIsInstance(output, FileOutput)
        self.assertIsNone(output.filename)
        self.assertIs(output.fd, stdout)
        self.assertIsInstance(output.record, FileOutput)
        self.assertEqual(output.record.filename, "foo")
        self.assertIsNone(output.record.fd)
        self.assertIsNone(output.record.record)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.check_file_output")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record(self, mock_check_file_output, args):
        # type: (Mock, Mock)
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
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "URL")
        self.assertIsInstance(output.record, FileOutput)
        self.assertEqual(output.record.filename, "foo")
        self.assertIsNone(output.record.fd)
        self.assertIsNone(output.record.record)

        args.title = "{author} - {title}"
        output = create_output(formatter)
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "foo - bar")
        self.assertIsInstance(output.record, FileOutput)
        self.assertEqual(output.record.filename, "foo")
        self.assertIsNone(output.record.fd)
        self.assertIsNone(output.record.record)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record_stdout(self, args):
        # type: (Mock)
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
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "foo - bar")
        self.assertIsInstance(output.record, FileOutput)
        self.assertIsNone(output.record.filename)
        self.assertEqual(output.record.fd, stdout)
        self.assertIsNone(output.record.record)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console")
    def test_create_output_record_and_other_file_output(self, console, args):
        # type: (Mock, Mock)
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record_and_pipe = True
        create_output(formatter)
        console.exit.assert_called_with("Cannot use record options with other file output options.")

    @patch("streamlink_cli.main.console")
    def test_create_output_no_default_player(self, console):
        # type: (Mock, Mock)
        streamlink_cli.main.args = args = Mock()
        console.exit = Mock()
        formatter = Formatter({})
        args.output = None
        args.stdout = False
        args.record_and_pipe = False
        args.player = None
        console.exit.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            create_output(formatter)
        if is_py2:
            self.assertRegexpMatches(
                console.exit.call_args_list[0][0][0],
                r"^The default player \(\w+\) does not seem to be installed\."
            )
        else:
            self.assertRegex(
                console.exit.call_args_list[0][0][0],
                r"^The default player \(\w+\) does not seem to be installed\."
            )


class TestCLIMainOutputStream(unittest.TestCase):
    @patch("streamlink_cli.main.args", Mock(retry_open=2))
    @patch("streamlink_cli.main.log")
    @patch("streamlink_cli.main.console")
    def test_stream_failure_no_output_open(self, mock_console, mock_log):
        # type: (Mock, Mock)
        output = Mock()
        stream = Mock(
            __str__=lambda _: "fake-stream",
            open=Mock(side_effect=StreamError("failure"))
        )
        formatter = Formatter({})

        with patch("streamlink_cli.main.output", Mock()), \
             patch("streamlink_cli.main.create_output", return_value=output):
            output_stream(formatter, stream, True)

        self.assertEqual(mock_log.error.call_args_list, [
            call("Try 1/2: Could not open stream fake-stream (Could not open stream: failure)"),
            call("Try 2/2: Could not open stream fake-stream (Could not open stream: failure)"),
        ])
        self.assertEqual(mock_console.exit.call_args_list, [
            call("Could not open stream fake-stream, tried 2 times, exiting")
        ])
        self.assertFalse(output.open.called, "Does not open the output on stream error")


class _TestCLIMainLogging(unittest.TestCase):
    @classmethod
    def subject(cls, argv, **kwargs):
        session = Streamlink()
        session.load_plugins(os.path.join(os.path.dirname(__file__), "plugin"))

        # stop test execution at the setup_signals() call, as we're not interested in what comes afterwards
        class StopTest(Exception):
            pass

        with patch("streamlink_cli.main.os.geteuid", create=True, new=Mock(return_value=kwargs.get("euid", 1000))), \
             patch("streamlink_cli.main.streamlink", session), \
             patch("streamlink_cli.main.setup_signals", side_effect=StopTest), \
             patch("streamlink_cli.main.CONFIG_FILES", ["/dev/null"]), \
             patch("streamlink_cli.main.setup_streamlink"), \
             patch("streamlink_cli.main.setup_plugins"), \
             patch("streamlink_cli.main.setup_http_session"), \
             patch("streamlink.session.Streamlink.load_builtin_plugins"), \
             patch("sys.argv") as mock_argv:
            mock_argv.__getitem__.side_effect = lambda x: argv[x]
            try:
                streamlink_cli.main.main()
            except StopTest:
                pass

    def tearDown(self):
        streamlink_cli.main.logger.root.handlers *= 0

    # python >=3.7.2: https://bugs.python.org/issue35046
    _write_call_log_cli_info = (
        ([call("[cli][info] foo\n")]
         if sys.version_info >= (3, 7, 2) or sys.version_info < (3, 0, 0)
         else [call("[cli][info] foo"), call("\n")])
    )
    _write_call_console_msg = [call("bar\n")]
    _write_call_console_msg_error = [call("error: bar\n")]
    _write_call_console_msg_json = [call("{\n  \"error\": \"bar\"\n}\n")]

    _write_calls = _write_call_log_cli_info + _write_call_console_msg

    def write_file_and_assert(self, mock_mkdir, mock_write, mock_stdout):
        # type: (Mock, Mock, Mock)
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(mock_mkdir.mock_calls, [call(parents=True, exist_ok=True)])
        self.assertEqual(mock_write.mock_calls, self._write_calls)
        self.assertFalse(mock_stdout.write.called)


class TestCLIMainLoggingStreams(_TestCLIMainLogging):
    # python >=3.7.2: https://bugs.python.org/issue35046
    _write_call_log_testcli_err = (
        [call("[test_cli_main][error] baz\n")]
        if sys.version_info >= (3, 7, 2) or sys.version_info < (3, 0, 0) else
        [call("[test_cli_main][error] baz"), call("\n")]
    )

    def subject(self, argv, stream=None):
        super(TestCLIMainLoggingStreams, self).subject(argv)
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
    def test_stream_stdout(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--stdout"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_output_eq_file(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--output=foo"], mock_stdout)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_output_eq_dash(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--output=-"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_eq_file(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--record=foo"], mock_stdout)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_eq_dash(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--record=-"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_stream_record_and_pipe(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--record-and-pipe=foo"], mock_stderr)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_no_pipe_no_json(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink"], mock_stdout)
        self.assertEqual(mock_stdout.write.mock_calls,
                         self._write_call_log_cli_info + self._write_call_log_testcli_err + self._write_call_console_msg_error)
        self.assertEqual(mock_stderr.write.mock_calls, [])

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_no_pipe_json(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--json"], mock_stdout)
        self.assertEqual(mock_stdout.write.mock_calls, self._write_call_console_msg_json)
        self.assertEqual(mock_stderr.write.mock_calls, [])

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_pipe_no_json(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--stdout"], mock_stderr)
        self.assertEqual(mock_stdout.write.mock_calls, [])
        self.assertEqual(mock_stderr.write.mock_calls,
                         self._write_call_log_cli_info + self._write_call_log_testcli_err + self._write_call_console_msg_error)

    @patch("sys.stderr")
    @patch("sys.stdout")
    def test_pipe_json(self, mock_stdout, mock_stderr):
        # type: (Mock, Mock)
        self.subject(["streamlink", "--stdout", "--json"], mock_stderr)
        self.assertEqual(mock_stdout.write.mock_calls, [])
        self.assertEqual(mock_stderr.write.mock_calls, self._write_call_console_msg_json)


class TestCLIMainLogging(_TestCLIMainLogging):
    @unittest.skipIf(is_win32, "test only applicable on a POSIX OS")
    @patch("streamlink_cli.main.log")
    def test_log_root_warning(self, mock_log):
        self.subject(["streamlink"], euid=0)
        self.assertEqual(mock_log.info.mock_calls, [call("streamlink is running as root! Be careful!")])

    @patch("streamlink_cli.main.log")
    @patch("streamlink_cli.main.streamlink_version", "streamlink")
    @patch("streamlink_cli.main.requests.__version__", "requests")
    @patch("streamlink_cli.main.socks_version", "socks")
    @patch("streamlink_cli.main.websocket_version", "websocket")
    @patch("platform.python_version", Mock(return_value="python"))
    def test_log_current_versions(self, mock_log):
        self.subject(["streamlink", "--loglevel", "info"])
        self.assertEqual(mock_log.debug.mock_calls, [], "Doesn't log anything if not debug logging")

        with patch("sys.platform", "linux"), \
             patch("platform.platform", Mock(return_value="linux")):
            self.subject(["streamlink", "--loglevel", "debug"])
            self.assertEqual(
                mock_log.debug.mock_calls[:4],
                [
                    call("OS:         linux"),
                    call("Python:     python"),
                    call("Streamlink: streamlink"),
                    call("Requests(requests), Socks(socks), Websocket(websocket)")
                ]
            )
            mock_log.debug.reset_mock()

        with patch("sys.platform", "win32"), \
             patch("platform.system", Mock(return_value="Windows")), \
             patch("platform.release", Mock(return_value="0.0.0")):
            self.subject(["streamlink", "--loglevel", "debug"])
            self.assertEqual(
                mock_log.debug.mock_calls[:4],
                [
                    call("OS:         Windows 0.0.0"),
                    call("Python:     python"),
                    call("Streamlink: streamlink"),
                    call("Requests(requests), Socks(socks), Websocket(websocket)")
                ]
            )
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
    @patch("io.open")
    def test_logfile_no_logfile(self, mock_open, mock_stdout):
        self.subject(["streamlink"])
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(streamlink_cli.main.console.output, sys.stdout)
        self.assertFalse(mock_open.called)
        self.assertEqual(mock_stdout.write.mock_calls, self._write_calls)

    @patch("sys.stdout")
    @patch("io.open")
    def test_logfile_loglevel_none(self, mock_open, mock_stdout):
        self.subject(["streamlink", "--loglevel", "none", "--logfile", "foo"])
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(streamlink_cli.main.console.output, sys.stdout)
        self.assertFalse(mock_open.called)
        self.assertEqual(mock_stdout.write.mock_calls, [call("bar\n")])


class TestCLIMainPrint(unittest.TestCase):
    def subject(self):
        with patch.object(Streamlink, "load_builtin_plugins"), \
             patch.object(Streamlink, "resolve_url") as mock_resolve_url, \
             patch.object(Streamlink, "resolve_url_no_redirect") as mock_resolve_url_no_redirect:
            session = Streamlink()
            session.load_plugins(os.path.join(os.path.dirname(__file__), "plugin"))
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
                  https://Billy2011.github.io/streamlink-27

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
