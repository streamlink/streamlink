import datetime
import os
import sys
import unittest
from pathlib import Path, PosixPath, WindowsPath
from unittest.mock import Mock, call, patch

import freezegun

import streamlink_cli.main
import tests.resources
from streamlink.session import Streamlink
from streamlink.stream.stream import Stream
from streamlink_cli.compat import DeprecatedPath, is_win32, stdout
from streamlink_cli.main import (
    Formatter,
    NoPluginError,
    check_file_output,
    create_output,
    format_valid_streams,
    handle_stream,
    handle_url,
    log_current_arguments,
    resolve_stream_name,
    setup_config_args
)
from streamlink_cli.output import FileOutput, PlayerOutput
from tests.plugin.testplugin import TestPlugin as FakePlugin


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
            format_valid_streams(FakePlugin, streams),
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
            format_valid_streams(FakePlugin, streams),
            ", ".join([
                "audio",
                "720p (worst-unfiltered)",
                "1080p (best-unfiltered)"
            ])
        )


class TestCLIMainJsonAndStreamUrl(unittest.TestCase):
    @patch("streamlink_cli.main.args", json=True, stream_url=True, subprocess_cmdline=False)
    @patch("streamlink_cli.main.console")
    def test_handle_stream_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(best=stream)
        plugin = FakePlugin("")
        plugin.module = "fake"
        plugin.arguments = []
        plugin.streams = Mock(return_value=streams)

        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [call(
            stream,
            metadata=dict(
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
        plugin = FakePlugin("")
        plugin.module = "fake"
        plugin.arguments = []
        plugin.streams = Mock(return_value=streams)

        with patch("streamlink_cli.main.streamlink", resolve_url=Mock(return_value=plugin)):
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [call(
                plugin="fake",
                metadata=dict(
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
    @patch("streamlink_cli.main.os.path.isfile", Mock(return_value=False))
    def test_check_file_output(self):
        output = check_file_output("foo", False)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, "foo")

    @patch("streamlink_cli.main.os.path.isfile", Mock(return_value=True))
    def test_check_file_output_exists_force(self):
        output = check_file_output("foo", True)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, "foo")

    @patch("streamlink_cli.main.console", Mock(ask=Mock(return_value="y")))
    @patch("streamlink_cli.main.os.path.isfile", Mock(return_value=True))
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_ask_yes(self, mock_sys: Mock):
        mock_sys.stdin.isatty.return_value = True
        output = check_file_output("foo", False)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, "foo")

    @patch("streamlink_cli.main.console", Mock(ask=Mock(return_value="N")))
    @patch("streamlink_cli.main.os.path.isfile", Mock(return_value=True))
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_ask_no(self, mock_sys: Mock):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.exit.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            check_file_output("foo", False)

    @patch("streamlink_cli.main.os.path.isfile", Mock(return_value=True))
    @patch("streamlink_cli.main.sys")
    def test_check_file_output_exists_notty(self, mock_sys: Mock):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.exit.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            check_file_output("foo", False)


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
        args.title = None
        args.url = "URL"
        args.player = "mpv"
        args.player_args = ""

        output = create_output(formatter)
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "URL")

        args.title = "{author} - {title}"
        output = create_output(formatter)
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "foo - bar")

    @patch("streamlink_cli.main.os.path.isfile")
    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    def test_create_output_file_output(self, args: Mock, mock_isfile):
        formatter = Formatter({})
        args.output = "foo"
        args.force = False
        args.fs_safe_rules = None
        mock_isfile.return_value = False

        output = create_output(formatter)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, "foo")
        self.assertEqual(output.fd, None)
        self.assertEqual(output.record, None)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    def test_create_output_stdout(self, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True

        output = create_output(formatter)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, None)
        self.assertEqual(output.fd, stdout)
        self.assertEqual(output.record, None)

        args.output = "-"
        args.stdout = False
        output = create_output(formatter)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, None)
        self.assertEqual(output.fd, stdout)
        self.assertEqual(output.record, None)

    @patch("streamlink_cli.main.os.path.isfile")
    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    def test_create_output_record_and_pipe(self, args: Mock, mock_isfile: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = None
        args.record_and_pipe = "foo"
        args.fs_safe_rules = None
        mock_isfile.return_value = False

        output = create_output(formatter)
        self.assertIsInstance(output, FileOutput)
        self.assertEqual(output.filename, None)
        self.assertEqual(output.fd, stdout)
        self.assertIsInstance(output.record, FileOutput)
        self.assertEqual(output.record.filename, "foo")
        self.assertEqual(output.record.fd, None)
        self.assertEqual(output.record.record, None)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console", Mock())
    @patch("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})
    def test_create_output_record(self, args: Mock):
        formatter = Formatter({
            "author": lambda: "foo"
        })
        args.output = None
        args.stdout = None
        args.record = "foo"
        args.record_and_pipe = None
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
        self.assertEqual(output.record.fd, None)
        self.assertEqual(output.record.record, None)

        args.title = "{author} - {title}"
        output = create_output(formatter)
        self.assertIsInstance(output, PlayerOutput)
        self.assertEqual(output.title, "foo - bar")
        self.assertIsInstance(output.record, FileOutput)
        self.assertEqual(output.record.filename, "foo")
        self.assertEqual(output.record.fd, None)
        self.assertEqual(output.record.record, None)

    @patch("streamlink_cli.main.args")
    @patch("streamlink_cli.main.console")
    def test_create_output_record_and_other_file_output(self, console: Mock, args: Mock):
        formatter = Formatter({})
        args.output = None
        args.stdout = True
        args.record_and_pipe = True
        create_output(formatter)
        console.exit.assert_called_with("Cannot use record options with other file output options.")


class TestCLIMainHandleStream(unittest.TestCase):
    @patch("streamlink_cli.main.output_stream")
    @patch("streamlink_cli.main.args")
    def test_handle_stream_output_stream(self, args: Mock, mock_output_stream: Mock):
        """
        Test that the formatter does define the correct variables
        """
        args.json = False
        args.subprocess_cmdline = False
        args.stream_url = False
        args.output = False
        args.stdout = False
        args.url = "URL"
        args.player_passthrough = []
        args.player_external_http = False
        args.player_continuous_http = False
        mock_output_stream.return_value = True

        plugin = FakePlugin("")
        plugin.author = "AUTHOR"
        plugin.category = "CATEGORY"
        plugin.title = "TITLE"
        stream = Stream(session=Mock())
        streams = {"best": stream}

        handle_stream(plugin, streams, "best")
        self.assertEqual(mock_output_stream.call_count, 1)
        paramStream, paramFormatter = mock_output_stream.call_args[0]
        self.assertIs(paramStream, stream)
        self.assertIsInstance(paramFormatter, Formatter)
        self.assertEqual(
            paramFormatter.title("{url} - {author} - {category}/{game} - {title}"),
            "URL - AUTHOR - CATEGORY/CATEGORY - TITLE"
        )


@patch("streamlink_cli.main.log")
class TestCLIMainSetupConfigArgs(unittest.TestCase):
    configdir = Path(tests.resources.__path__[0], "cli", "config")
    parser = Mock()

    @classmethod
    def subject(cls, config_files, **args):
        def resolve_url(name):
            if name == "noplugin":
                raise NoPluginError()
            return Mock(module="testplugin")

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
        self.assertEqual(mock_log.info.mock_calls, [])

    def test_default_primary(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=None
        )
        expected = [self.configdir / "primary", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        self.assertEqual(mock_log.info.mock_calls, [])

    def test_default_secondary_deprecated(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "non-existent", DeprecatedPath(self.configdir / "secondary")],
            config=None
        )
        expected = [self.configdir / "secondary", self.configdir / "secondary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        self.assertEqual(mock_log.info.mock_calls, [
            call(f"Loaded config from deprecated path, see CLI docs for how to migrate: {expected[0]}"),
            call(f"Loaded plugin config from deprecated path, see CLI docs for how to migrate: {expected[1]}")
        ])

    def test_custom_with_primary_plugin(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "custom")]
        )
        expected = [self.configdir / "custom", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        self.assertEqual(mock_log.info.mock_calls, [])

    def test_custom_with_deprecated_plugin(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "non-existent", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "custom")]
        )
        expected = [self.configdir / "custom", DeprecatedPath(self.configdir / "secondary.testplugin")]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        self.assertEqual(mock_log.info.mock_calls, [
            call(f"Loaded plugin config from deprecated path, see CLI docs for how to migrate: {expected[1]}")
        ])

    def test_custom_multiple(self, mock_log):
        mock_setup_args = self.subject(
            [self.configdir / "primary", DeprecatedPath(self.configdir / "secondary")],
            config=[str(self.configdir / "non-existent"), str(self.configdir / "primary"), str(self.configdir / "secondary")]
        )
        expected = [self.configdir / "secondary", self.configdir / "primary", self.configdir / "primary.testplugin"]
        mock_setup_args.assert_called_once_with(self.parser, expected, ignore_unknown=False)
        self.assertEqual(mock_log.info.mock_calls, [])


class _TestCLIMainLogging(unittest.TestCase):
    @classmethod
    def subject(cls, argv):
        session = Streamlink()
        session.load_plugins(os.path.join(os.path.dirname(__file__), "plugin"))

        def _log_current_arguments(*args, **kwargs):
            log_current_arguments(*args, **kwargs)
            raise SystemExit

        with patch("streamlink_cli.main.streamlink", session), \
             patch("streamlink_cli.main.log_current_arguments", side_effect=_log_current_arguments), \
             patch("streamlink_cli.main.CONFIG_FILES", []), \
             patch("streamlink_cli.main.setup_signals"), \
             patch("streamlink_cli.main.setup_streamlink"), \
             patch("streamlink_cli.main.setup_plugins"), \
             patch("streamlink_cli.main.setup_http_session"), \
             patch("streamlink.session.Streamlink.load_builtin_plugins"), \
             patch("sys.argv") as mock_argv:
            mock_argv.__getitem__.side_effect = lambda x: argv[x]
            try:
                streamlink_cli.main.main()
            except SystemExit:
                pass

    def tearDown(self):
        streamlink_cli.main.logger.root.handlers.clear()

    # python >=3.7.2: https://bugs.python.org/issue35046
    _write_calls = (
        ([call("[cli][info] foo\n")]
         if sys.version_info >= (3, 7, 2)
         else [call("[cli][info] foo"), call("\n")])
        + [call("bar\n")]
    )

    def write_file_and_assert(self, mock_mkdir: Mock, mock_write: Mock, mock_stdout: Mock):
        streamlink_cli.main.log.info("foo")
        streamlink_cli.main.console.msg("bar")
        self.assertEqual(mock_mkdir.mock_calls, [call(parents=True, exist_ok=True)])
        self.assertEqual(mock_write.mock_calls, self._write_calls)
        self.assertFalse(mock_stdout.write.called)


class TestCLIMainLogging(_TestCLIMainLogging):
    @unittest.skipIf(is_win32, "test only applicable on a POSIX OS")
    @patch("streamlink_cli.main.log")
    @patch("streamlink_cli.main.os.geteuid", Mock(return_value=0))
    def test_log_root_warning(self, mock_log):
        self.subject(["streamlink"])
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

        with patch("sys.platform", "darwin"), \
             patch("platform.mac_ver", Mock(return_value=["0.0.0"])):
            self.subject(["streamlink", "--loglevel", "debug"])
            self.assertEqual(
                mock_log.debug.mock_calls[:4],
                [
                    call("OS:         macOS 0.0.0"),
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


@unittest.skipIf(is_win32, "test only applicable on a POSIX OS")
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


@unittest.skipIf(not is_win32, "test only applicable on Windows")
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
