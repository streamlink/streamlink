from __future__ import annotations

import argparse
import warnings
from io import StringIO
from queue import Empty, Queue
from threading import Event, Thread
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import streamlink_cli.main
from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink_cli.argparser import ArgumentParser
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.setup_args import setup_args_from_stdin


if TYPE_CHECKING:
    from pathlib import Path


def test_parse_error(capsys: pytest.CaptureFixture[str], argv: list[str]):
    argv.append("--loglevel=doesnotexist")

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 2

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr.startswith("streamlink: error: argument -l/--loglevel: invalid choice: 'doesnotexist'")


def test_unknown(capsys: pytest.CaptureFixture[str], argv: list[str]):
    argv.append("--doesnotexist")

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 2

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr.endswith("streamlink: error: unrecognized arguments: --doesnotexist\n")


@pytest.mark.parametrize("argv", [["foo"], ["--url=foo"], ["foo", "--url=bar"]], indirect=["argv"])
def test_url_param(monkeypatch: pytest.MonkeyPatch, argv: list[str]):
    monkeypatch.setattr("streamlink_cli.main.run", lambda *_, **__: 123)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 123

    assert streamlink_cli.main.args.url == "foo"


def test_stream_param(monkeypatch: pytest.MonkeyPatch, argv: list[str]):
    argv.extend(["foo", "BEST,WORST"])
    monkeypatch.setattr("streamlink_cli.main.run", lambda *_, **__: 123)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 123

    assert streamlink_cli.main.args.stream == ["best", "worst"]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        pytest.param([], False, id="empty"),
        pytest.param(["foo"], False, id="other"),
        pytest.param(["--quiet"], True, id="quiet"),
        pytest.param(["--json"], True, id="json"),
        pytest.param(["--stream-url"], True, id="stream-url"),
    ],
    indirect=["argv"],
)
def test_silent_log(monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: bool):
    monkeypatch.setattr("streamlink_cli.main.run", lambda *_, **__: 123)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 123

    assert streamlink_cli.main.args.silent_log is expected


def test_streamlinkdeprecationwarning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    recwarn: pytest.WarningsRecorder,
    argv: list[str],
):
    original_build_parser = streamlink_cli.main.build_parser

    class DeprecatedAction(argparse._StoreConstAction):
        def __call__(self, *args, **kwargs):
            super().__call__(*args, **kwargs)
            warnings.warn(f"DEPRECATED: {self.const}", StreamlinkDeprecationWarning, stacklevel=1)

    def mocked_build_parser():
        parser = original_build_parser()
        parser.add_argument("--deprecated-one", action=DeprecatedAction, const="one")
        parser.add_argument("--deprecated-two", action=DeprecatedAction, const="two")
        return parser

    config_file = tmp_path / "config"
    config_file.write_text("deprecated-two", encoding="utf-8")

    monkeypatch.setattr(streamlink_cli.main, "build_parser", mocked_build_parser)
    monkeypatch.setattr("streamlink_cli.main.run", lambda *_, **__: 123)
    argv.extend(["--config", str(config_file), "--deprecated-one"])

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 123

    assert [(item.category, str(item.message)) for item in recwarn.list] == []
    assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
        ("streamlinkdeprecation", "warning", "DEPRECATED: one"),
        ("streamlinkdeprecation", "warning", "DEPRECATED: two"),
    ]


class TestArgsFromStdin:
    # noinspection nested-decorators
    @pytest.fixture(scope="class")
    @classmethod
    def parser(cls):
        return ArgumentParser()

    @pytest.fixture(autouse=True)
    def thread(self, monkeypatch: pytest.MonkeyPatch):
        class Recorder:
            thread: Thread | None = None

        class FakeThread(Thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                Recorder.thread = self

        monkeypatch.setattr("streamlink_cli.setup_args.Thread", FakeThread)
        yield Recorder
        assert not Recorder.thread or not Recorder.thread.is_alive()

    def test_disabled(self, caplog: pytest.LogCaptureFixture, parser: ArgumentParser):
        assert setup_args_from_stdin(parser, args_from_stdin=False) == []
        assert caplog.records == []

    @pytest.mark.parametrize(
        ("stdin", "logs"),
        [
            pytest.param(
                None,
                [],
                id="none",
            ),
            pytest.param(
                Mock(closed=True),
                [],
                id="closed",
            ),
            pytest.param(
                Mock(closed=False, isatty=Mock(return_value=True)),
                [("streamlink.cli", "warning", "Can't process arguments from a TTY stdin stream")],
                id="isatty",
            ),
        ],
    )
    def test_stdin(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        parser: ArgumentParser,
        stdin: Mock,
        logs: list,
    ):
        monkeypatch.setattr("streamlink_cli.setup_args.sys", Mock(stdin=stdin))
        assert setup_args_from_stdin(parser, args_from_stdin=True) == []
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == logs

    def test_worker_simple(self, monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser):
        fakestdin = StringIO("foo\nbar=123\nbaz 456\n\nqux\n")
        monkeypatch.setattr("streamlink_cli.setup_args.sys", Mock(stdin=fakestdin))
        assert setup_args_from_stdin(parser, args_from_stdin=True) == ["--foo", "--bar=123", "--baz=456"]
        assert fakestdin.closed

    def test_worker_no_nl(self, monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser):
        fakestdin = StringIO("foo")
        monkeypatch.setattr("streamlink_cli.setup_args.sys", Mock(stdin=fakestdin))
        with pytest.raises(StreamlinkCLIError, match=r"^Missing argument line terminator in stdin input$") as exc_info:
            setup_args_from_stdin(parser, args_from_stdin=True)
        assert type(exc_info.value.__cause__) is RuntimeError
        assert fakestdin.closed

    def test_worker_no_eof(self, monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser):
        class FakeStdin(StringIO):
            def close(self):
                super().close()
                event.set()

            def readline(self, *_, **__):
                event.wait(timeout=4.0)
                return ""

        event = Event()
        fakestdin = FakeStdin()

        monkeypatch.setattr("streamlink_cli.setup_args.sys", Mock(stdin=fakestdin))
        monkeypatch.setattr("streamlink_cli.setup_args.Queue.get", Mock(side_effect=Empty))
        with pytest.raises(StreamlinkCLIError, match=r"^Timeout while reading arguments from stdin$"):
            setup_args_from_stdin(parser, args_from_stdin=True)
        assert fakestdin.closed

    def test_worker_put_block(self, monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser):
        class FakeQueue(Queue):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.filled = Event()

            def put(self, *args, **kwargs):
                super().put(*args, **kwargs)
                self.filled.set()

            def get(self, *_, **__):
                self.filled.wait(timeout=4.0)

        fakestdin = StringIO("foo\nbar\nbaz\n")
        monkeypatch.setattr("streamlink_cli.setup_args.sys", Mock(stdin=fakestdin))
        monkeypatch.setattr("streamlink_cli.setup_args.Queue", FakeQueue)
        setup_args_from_stdin(parser, args_from_stdin=True, max_queue_size=1)
        assert fakestdin.closed


@pytest.mark.parametrize(
    ("argv", "stdin", "configfile", "expected"),
    [
        pytest.param(["-l", "debug"], "", "", {"loglevel": "debug"}, id="argv"),
        pytest.param([], "l debug\n", "", {"loglevel": "debug"}, id="stdin"),
        pytest.param([], "", "l debug\n", {"loglevel": "debug"}, id="configfile"),
        pytest.param([], "l info\n", "l debug\n", {"loglevel": "info"}, id="stdin-overrides-configfile"),
        pytest.param(["-l", "info"], "l debug\n", "", {"loglevel": "info"}, id="argv-overrides-stdin"),
        pytest.param(["-l", "info"], "", "l debug\n", {"loglevel": "info"}, id="argv-overrides-configfile"),
        pytest.param(["-l", "info"], "l warning\n", "l debug\n", {"loglevel": "info"}, id="argv-overrides-both"),
    ],
    indirect=["argv"],
)
def test_mixing_argv_stdin_configfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list,
    stdin: str,
    configfile: str,
    expected: dict,
):
    monkeypatch.setattr("streamlink_cli.main.run", lambda *_, **__: 123)

    fake_stdin = StringIO(stdin)
    monkeypatch.setattr("sys.stdin", fake_stdin)

    config_file = tmp_path / "config"
    with config_file.open(mode="w") as fd:
        fd.write(configfile)

    argv.extend(["--args-from-stdin", "--config", str(config_file)])

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 123

    assert {key: getattr(streamlink_cli.main.args, key, None) for key in expected.keys()} == expected


def test_args_from_stdin_applied_early(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list):
    fake_stdin = StringIO("quiet\n")
    argv.append("--args-from-stdin")
    monkeypatch.setattr("sys.stdin", fake_stdin)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 0

    stdout, stderr = capsys.readouterr()
    assert not stdout
    assert not stderr
