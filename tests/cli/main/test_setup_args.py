from __future__ import annotations

import argparse
import warnings
from typing import TYPE_CHECKING

import pytest

import streamlink_cli.main
from streamlink.exceptions import StreamlinkDeprecationWarning


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
