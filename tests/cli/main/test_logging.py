import logging
import sys
from errno import EINVAL, EPIPE
from io import StringIO
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock, call

import pytest

import streamlink_cli.main
import tests
from streamlink.logger import ALL, TRACE, StringFormatter
from streamlink.session import Streamlink
from streamlink_cli.argparser import ArgumentParser
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.main import build_parser


@pytest.fixture(autouse=True)
def session(session: Streamlink):
    session.plugins.load_path(Path(tests.__path__[0]) / "plugin")

    return session


@pytest.fixture()
def parser():
    return build_parser()


class TestStdoutStderr:
    @pytest.fixture(autouse=True)
    def _no_debug_logs(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink_cli.main.log_root_warning", Mock())
        monkeypatch.setattr("streamlink_cli.main.log_current_versions", Mock())
        monkeypatch.setattr("streamlink_cli.main.log_current_arguments", Mock())

    # noinspection PyUnresolvedReferences
    @pytest.mark.parametrize(
        ("argv", "stream"),
        [
            pytest.param([], "stdout", id="default"),
            pytest.param(["--stdout"], "stderr", id="--stdout"),
            pytest.param(["--output=file"], "stdout", id="--output=file"),
            pytest.param(["--output=-"], "stderr", id="--output=-"),
            pytest.param(["--record=file"], "stdout", id="--record=file"),
            pytest.param(["--record=-"], "stderr", id="--record=-"),
            pytest.param(["--record-and-pipe=file"], "stderr", id="--record-and-pipe=file"),
        ],
        indirect=["argv"],
    )
    def test_streams(self, capsys: pytest.CaptureFixture, parser: ArgumentParser, argv: list, stream: str):
        streamlink_cli.main.setup(parser)

        rootlogger = logging.getLogger("streamlink")
        clilogger = streamlink_cli.main.log
        streamobj = getattr(sys, stream)

        assert clilogger.parent is rootlogger
        assert isinstance(rootlogger.handlers[0], logging.StreamHandler)
        assert rootlogger.handlers[0].stream is streamobj
        assert streamlink_cli.main.console.output is streamobj

    @pytest.mark.parametrize(
        ("argv", "stdout", "stderr"),
        [
            pytest.param([], "[cli][info] a\n[test_main_logging][error] b\nerror: c\n", "", id="no-pipe-no-json"),
            pytest.param(["--json"], '{\n  "error": "c"\n}\n', "", id="no-pipe-json"),
            pytest.param(["--stdout"], "", "[cli][info] a\n[test_main_logging][error] b\nerror: c\n", id="pipe-no-json"),
            pytest.param(["--stdout", "--json"], "", '{\n  "error": "c"\n}\n', id="pipe-json"),
        ],
        indirect=["argv"],
    )
    def test_output(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        argv: list,
        stdout: str,
        stderr: str,
    ):
        def run(_parser):
            childlogger = logging.getLogger("streamlink.test_main_logging")
            streamlink_cli.main.log.info("a")
            childlogger.error("b")
            raise StreamlinkCLIError("c")

        monkeypatch.setattr("streamlink_cli.main.run", run)

        with pytest.raises(SystemExit) as excinfo:
            streamlink_cli.main.main()
        assert excinfo.value.code == 1

        out, err = capsys.readouterr()
        assert out == stdout
        assert err == stderr

    def test_no_stdout(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("sys.stdout", None)

        with pytest.raises(SystemExit) as excinfo:
            streamlink_cli.main.main()
        assert excinfo.value.code == 0

    @pytest.mark.parametrize(
        "errno",
        [
            pytest.param(EPIPE, id="EPIPE", marks=pytest.mark.posix_only),
            pytest.param(EINVAL, id="EINVAL", marks=pytest.mark.windows_only),
        ],
    )
    @pytest.mark.parametrize(
        "code",
        [0, 1],
    )
    def test_brokenpipeerror(self, monkeypatch: pytest.MonkeyPatch, errno: int, code: int):
        def run(*_, **__):
            def flush(*_, **__):
                try:
                    exception = OSError()
                    exception.errno = errno
                    raise exception
                finally:
                    monkeypatch.undo()

            monkeypatch.setattr("sys.stdout.flush", flush)

            return code

        monkeypatch.setattr("streamlink_cli.main.run", run)

        with pytest.raises(SystemExit) as excinfo:
            streamlink_cli.main.main()
        assert excinfo.value.code == code

    def test_setup_uncaught_exceptions(self, monkeypatch: pytest.MonkeyPatch):
        exception = Exception()
        monkeypatch.setattr("streamlink_cli.main.setup", Mock(side_effect=exception))

        with pytest.raises(Exception) as excinfo:  # noqa: PT011
            streamlink_cli.main.main()
        assert excinfo.value is exception, "Does not catch non-StreamlinkCLIError exceptions"

    @pytest.mark.parametrize(
        ("argv", "msg"),
        [
            pytest.param(
                ["--logformat", "message"],
                "Logging setup error: invalid format: no fields\n",
                id="no-fields",
            ),
            pytest.param(
                ["--logformat", "%(message)s"],
                "Logging setup error: invalid format: no fields\n",
                id="wrong-style",
            ),
            pytest.param(
                ["--logformat", "{doesnotexist}"],
                "Logging setup error: Formatting field not found in record: 'doesnotexist'\n",
                id="field-not-found",
            ),
        ],
        indirect=["argv"],
    )
    def test_logging_setup_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        argv: list,
        msg: str,
    ):
        mock_run = Mock()
        monkeypatch.setattr("streamlink_cli.main.run", mock_run)

        with pytest.raises(SystemExit) as excinfo:
            streamlink_cli.main.main()
        assert excinfo.value.code == 1
        assert not mock_run.called

        out, err = capsys.readouterr()
        assert out == ""
        assert err == msg


class TestInfos:
    # noinspection PyTestParametrized
    @pytest.mark.posix_only()
    @pytest.mark.parametrize(
        ("_euid", "logs"),
        [
            pytest.param(1000, [], id="user"),
            pytest.param(0, [("cli", "info", "streamlink is running as root! Be careful!")], id="root"),
        ],
        indirect=["_euid"],
    )
    def test_log_root_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        parser: ArgumentParser,
        logs: list,
    ):
        monkeypatch.setattr("streamlink_cli.main.log_current_versions", Mock())
        monkeypatch.setattr("streamlink_cli.main.log_current_arguments", Mock())

        streamlink_cli.main.setup(parser)
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == logs

    @pytest.mark.parametrize(
        ("argv", "platform", "logs"),
        [
            pytest.param(
                ["--loglevel", "info"],
                "linux",
                [],
                id="non-debug-loglevel",
            ),
            pytest.param(
                ["--loglevel", "debug"],
                "darwin",
                [
                    ("cli", "debug", "OS:         macOS 0.0.0"),
                    ("cli", "debug", "Python:     PYTHON_VERSION"),
                    ("cli", "debug", "OpenSSL:    OPENSSL_VERSION"),
                    ("cli", "debug", "Streamlink: STREAMLINK_VERSION"),
                    ("cli", "debug", "Dependencies:"),
                    ("cli", "debug", " bar-baz: 2.0.0"),
                    ("cli", "debug", " foo: 1.2.3"),
                ],
                id="darwin",
            ),
            pytest.param(
                ["--loglevel", "debug"],
                "win32",
                [
                    ("cli", "debug", "OS:         Windows 0.0.0"),
                    ("cli", "debug", "Python:     PYTHON_VERSION"),
                    ("cli", "debug", "OpenSSL:    OPENSSL_VERSION"),
                    ("cli", "debug", "Streamlink: STREAMLINK_VERSION"),
                    ("cli", "debug", "Dependencies:"),
                    ("cli", "debug", " bar-baz: 2.0.0"),
                    ("cli", "debug", " foo: 1.2.3"),
                ],
                id="win32",
            ),
            pytest.param(
                ["--loglevel", "debug"],
                "linux",
                [
                    ("cli", "debug", "OS:         linux"),
                    ("cli", "debug", "Python:     PYTHON_VERSION"),
                    ("cli", "debug", "OpenSSL:    OPENSSL_VERSION"),
                    ("cli", "debug", "Streamlink: STREAMLINK_VERSION"),
                    ("cli", "debug", "Dependencies:"),
                    ("cli", "debug", " bar-baz: 2.0.0"),
                    ("cli", "debug", " foo: 1.2.3"),
                ],
                id="linux",
            ),
        ],
        indirect=["argv"],
    )
    def test_log_current_versions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        parser: ArgumentParser,
        argv: list,
        platform: str,
        logs: list,
    ):
        class FakePackageNotFoundError(Exception):
            pass

        def version(dist):
            if dist == "foo":
                return "1.2.3"
            if dist == "bar-baz":
                return "2.0.0"
            raise FakePackageNotFoundError()

        mock_importlib_metadata = Mock()
        mock_importlib_metadata.PackageNotFoundError = FakePackageNotFoundError
        mock_importlib_metadata.requires.return_value = [
            "foo>1 ; python_version>='3.13'",
            "foo<=1 ; python_version<'3.13'",
            "bar-baz==2",
            "qux~=3",
        ]
        mock_importlib_metadata.version.side_effect = version

        monkeypatch.setattr("importlib.metadata", mock_importlib_metadata)
        monkeypatch.setattr("platform.python_version", Mock(return_value="PYTHON_VERSION"))
        monkeypatch.setattr("ssl.OPENSSL_VERSION", "OPENSSL_VERSION")
        monkeypatch.setattr("streamlink_cli.main.streamlink_version", "STREAMLINK_VERSION")
        monkeypatch.setattr("streamlink_cli.main.log_root_warning", Mock())
        monkeypatch.setattr("streamlink_cli.main.log_current_arguments", Mock())

        monkeypatch.setattr("sys.platform", platform)
        monkeypatch.setattr("platform.mac_ver", Mock(return_value=["0.0.0"]))
        monkeypatch.setattr("platform.system", Mock(return_value="Windows"))
        monkeypatch.setattr("platform.release", Mock(return_value="0.0.0"))
        monkeypatch.setattr("platform.platform", Mock(return_value="linux"))

        streamlink_cli.main.setup(parser)
        assert mock_importlib_metadata.requires.call_args_list == ([call("streamlink")] if logs else [])
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == logs

    @pytest.mark.parametrize(
        ("argv", "logs"),
        [
            pytest.param(
                ["--loglevel", "info"],
                [],
                id="non-debug-loglevel",
            ),
            pytest.param(
                [
                    "--loglevel",
                    "debug",
                    "-p",
                    "custom",
                    "--testplugin-bool",
                    "--testplugin-password=secret",
                    "test.se/channel",
                    "best,worst",
                ],
                [
                    ("cli", "debug", "Arguments:"),
                    ("cli", "debug", " url=test.se/channel"),
                    ("cli", "debug", " stream=['best', 'worst']"),
                    ("cli", "debug", " --loglevel=debug"),
                    ("cli", "debug", " --player=custom"),
                    ("cli", "debug", " --testplugin-bool=True"),
                    ("cli", "debug", " --testplugin-password=********"),
                ],
                id="arguments",
            ),
        ],
        indirect=["argv"],
    )
    def test_log_current_arguments(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        parser: ArgumentParser,
        argv: list,
        logs: list,
    ):
        monkeypatch.setattr("streamlink_cli.main.log_root_warning", Mock())
        monkeypatch.setattr("streamlink_cli.main.log_current_versions", Mock())

        streamlink_cli.main.setup(parser)
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == logs


@pytest.mark.parametrize(
    ("argv", "level", "fmt", "datefmt"),
    [
        pytest.param(
            [],
            logging.INFO,
            "[{name}][{levelname}] {message}",
            "%H:%M:%S",
            id="default",
        ),
        pytest.param(
            ["--loglevel", "trace"],
            TRACE,
            "[{asctime}][{name}][{levelname}] {message}",
            "%H:%M:%S.%f",
            id="loglevel=trace",
        ),
        pytest.param(
            ["--loglevel", "all"],
            ALL,
            "[{asctime}][{name}][{levelname}] {message}",
            "%H:%M:%S.%f",
            id="loglevel=all",
        ),
        pytest.param(
            ["--loglevel", "all", "--logformat", "{asctime} - {message}"],
            ALL,
            "{asctime} - {message}",
            "%H:%M:%S.%f",
            id="logformat",
        ),
        pytest.param(
            ["--loglevel", "all", "--logdateformat", "%Y-%m-%dT%H:%M:%S.%f"],
            ALL,
            "[{asctime}][{name}][{levelname}] {message}",
            "%Y-%m-%dT%H:%M:%S.%f",
            id="logdateformat",
        ),
    ],
    indirect=["argv"],
)
def test_logformat(argv: list, parser: ArgumentParser, level: int, fmt: str, datefmt: str):
    streamlink_cli.main.setup(parser)

    rootlogger = logging.getLogger("streamlink")
    assert rootlogger.level == level
    assert rootlogger.handlers
    formatter = rootlogger.handlers[0].formatter
    assert isinstance(formatter, StringFormatter)
    assert isinstance(formatter._style, logging.StrFormatStyle)
    assert formatter._fmt == fmt
    assert formatter.datefmt == datefmt


class TestLogfile:
    @pytest.fixture(autouse=True)
    def _time(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink_cli.main.datetime", Mock(now=Mock(return_value="2000-01-01_12-34-56")))

    @pytest.fixture(autouse=True)
    def logpath(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        home = tmp_path / "user"
        logdir = home / "logs"

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        monkeypatch.setattr("streamlink_cli.main.LOG_DIR", logdir)

        return tmp_path

    # noinspection PyUnresolvedReferences
    @pytest.mark.parametrize(
        ("argv", "stdout", "stderr"),
        [
            pytest.param(
                [],
                "[cli][info] a\nb\n",
                "",
                id="no-logfile",
            ),
            pytest.param(
                ["--logfile=file", "--loglevel=none"],
                "b\n",
                "",
                id="logfile-loglevel-none",
            ),
        ],
        indirect=["argv"],
    )
    def test_no_logfile(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        parser: ArgumentParser,
        argv: list,
        stdout: str,
        stderr: str,
    ):
        mock_open = Mock()
        monkeypatch.setattr("builtins.open", mock_open)

        streamlink_cli.main.setup(parser)

        rootlogger = logging.getLogger("streamlink")
        assert isinstance(rootlogger.handlers[0], logging.StreamHandler)
        assert rootlogger.handlers[0].stream is sys.stdout
        assert streamlink_cli.main.console.output is sys.stdout

        streamlink_cli.main.log.info("a")
        streamlink_cli.main.console.msg("b")
        out, err = capsys.readouterr()
        assert not mock_open.called
        assert out == stdout
        assert err == stderr

    # noinspection PyUnresolvedReferences
    @pytest.mark.parametrize(
        ("argv", "path", "content"),
        [
            pytest.param(
                ["--logfile=path/to/logfile"],
                Path("path", "to", "logfile"),
                "[cli][info] a\nb\n",
                id="logfile-path-resolve",
            ),
            pytest.param(
                ["--logfile=~/path/to/logfile"],
                Path("user", "path", "to", "logfile"),
                "[cli][info] a\nb\n",
                id="logfile-path-expanduser",
            ),
            pytest.param(
                ["--logfile=-"],
                Path("user", "logs", "2000-01-01_12-34-56.log"),
                "[cli][info] a\nb\n",
                id="logfile-auto",
            ),
        ],
        indirect=["argv"],
    )
    def test_logfile(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        parser: ArgumentParser,
        logpath: Path,
        argv: list,
        path: str,
        content: str,
    ):
        abspath = Path().resolve() / path

        streamobj = StringIO()
        mock_open = Mock(return_value=streamobj)
        monkeypatch.setattr("builtins.open", mock_open)

        streamlink_cli.main.setup(parser)
        assert abspath.parent.exists()

        rootlogger = logging.getLogger("streamlink")
        assert isinstance(rootlogger.handlers[0], logging.FileHandler)
        assert rootlogger.handlers[0].baseFilename == str(abspath)
        assert rootlogger.handlers[0].stream is streamobj
        assert streamlink_cli.main.console.output is streamobj

        streamlink_cli.main.log.info("a")
        streamlink_cli.main.console.msg("b")
        out, err = capsys.readouterr()
        assert mock_open.call_args_list == [call(str(abspath), "a", encoding="utf-8", errors=None)]
        assert streamobj.getvalue() == content
        assert out == ""
        assert err == ""


class TestPrint:
    @pytest.fixture(autouse=True)
    def stdout(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, session: Streamlink):
        mock_resolve_url = Mock()
        monkeypatch.setattr(session, "resolve_url", mock_resolve_url)

        with pytest.raises(SystemExit) as cm:
            streamlink_cli.main.main()
        assert cm.value.code == 0
        assert mock_resolve_url.call_args_list == []

        out, err = capsys.readouterr()
        assert err == ""

        return out

    def test_usage(self, stdout: str):
        assert (
            stdout
            == dedent("""
                usage: streamlink [OPTIONS] <URL> [STREAM]

                Use -h/--help to see the available options or read the manual at https://streamlink.github.io/
            """).lstrip()
        )

    @pytest.mark.parametrize("argv", [["--help"]], indirect=["argv"])
    def test_help(self, argv: list, stdout: str):
        assert "usage: streamlink [OPTIONS] <URL> [STREAM]" in stdout
        assert (
            dedent("""
                Streamlink is a command-line utility that extracts streams from various
                services and pipes them into a video player of choice.
            """)
            in stdout
        )
        assert (
            dedent("""
                For more in-depth documentation see:
                  https://streamlink.github.io/

                Please report broken plugins or bugs to the issue tracker on GitHub:
                  https://github.com/streamlink/streamlink/issues
            """)
            in stdout
        )

    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            pytest.param(["--plugins"], "Available plugins: testplugin\n", id="plugins-no-json"),
            pytest.param(["--plugins", "--json"], """[\n  "testplugin"\n]\n""", id="plugins-json"),
        ],
        indirect=["argv"],
    )
    def test_plugins(self, argv: list, expected: str, stdout: str):
        assert stdout == expected
