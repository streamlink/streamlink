from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call, sentinel

import pytest

import streamlink_cli.main
from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink_cli.constants import PROGRESS_INTERVAL_NO_STATUS
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.main import build_parser, setup_args
from streamlink_cli.output import FileOutput, PlayerOutput


@pytest.fixture(autouse=True)
def argv(argv: list):
    parser = build_parser()
    setup_args(parser)

    return argv


@pytest.fixture()
def caplog(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink.cli")
    return caplog


@pytest.fixture(autouse=True)
def output(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    output = getattr(request, "param", Mock())
    monkeypatch.setattr(streamlink_cli.main, "output", output)
    monkeypatch.setattr(streamlink_cli.main, "create_output", Mock(return_value=output))
    monkeypatch.setattr(output, "open", Mock())

    return output


@pytest.fixture()
def stream(monkeypatch: pytest.MonkeyPatch):
    class FakeStream(Stream):
        __shortname__ = "fake-stream"

        def __str__(self):
            return self.__shortname__

    return FakeStream(Mock())


@pytest.mark.parametrize("argv", [pytest.param(["--retry-open=2"])], indirect=True)
def test_stream_failure_no_output_open(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    argv: list,
    output: Mock,
    stream: Stream,
):
    monkeypatch.setattr(stream, "open", Mock(side_effect=StreamError("failure")))

    with pytest.raises(StreamlinkCLIError) as exc_info:
        streamlink_cli.main.output_stream(stream, Mock())

    assert [(record.levelname, record.module, record.message) for record in caplog.records] == [
        ("error", "main", "Try 1/2: Could not open stream fake-stream (Could not open stream: failure)"),
        ("error", "main", "Try 2/2: Could not open stream fake-stream (Could not open stream: failure)"),
    ]
    assert not output.open.called, "Does not open the output on stream error"
    assert str(exc_info.value) == "Could not open stream fake-stream, tried 2 times, exiting"
    assert exc_info.value.code == 1


@pytest.mark.parametrize("argv", [["--retry-open=1"]], indirect=True)
@pytest.mark.parametrize("has_progress", [True, False])
def test_stream_runner_with_progress(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    argv: list,
    stream: Stream,
    output: PlayerOutput | FileOutput,
    has_progress: bool,
):
    streamio = BytesIO(b"0" * 8192 * 2)
    monkeypatch.setattr(stream, "open", Mock(return_value=streamio))

    mock_streamrunner = Mock()
    monkeypatch.setattr(streamlink_cli.main, "StreamRunner", mock_streamrunner)

    progress = sentinel.progress if has_progress else None
    monkeypatch.setattr(streamlink_cli.main, "get_output_progress", Mock(return_value=progress))

    assert streamlink_cli.main.output_stream(stream, Mock())

    assert [(record.levelname, record.module, record.message) for record in caplog.records] == [
        ("debug", "main", "Pre-buffering 8192 bytes"),
        ("debug", "main", "Writing stream to output"),
    ]
    assert mock_streamrunner.call_args_list == [call(streamio, output, progress=progress)]


filename = Path("filename")
file_output = FileOutput(filename)
file_recording = FileOutput(record=file_output)
player_output = PlayerOutput(Path("player"))
player_recording = PlayerOutput(Path("player"), record=file_output)


@pytest.mark.parametrize(
    ("argv", "supports_status_messages", "output", "expected"),
    [
        pytest.param(
            ["--progress=yes"],
            True,
            player_recording,
            {"path": filename},
            id="progress-status-messages-playeroutput-recording",
        ),
        pytest.param(
            ["--progress=yes"],
            True,
            file_output,
            {"path": filename},
            id="progress-status-messages-fileoutput",
        ),
        pytest.param(
            ["--progress=yes"],
            True,
            file_recording,
            {"path": filename},
            id="progress-status-messages-fileoutput-recording",
        ),
        pytest.param(
            ["--progress=yes"],
            True,
            player_output,
            {},
            id="progress-playeroutput-no-recording",
        ),
        pytest.param(
            ["--progress=yes"],
            True,
            file_output,
            {"path": filename},
            id="progress-fileoutput-no-recording",
        ),
        pytest.param(
            ["--progress=no"],
            True,
            file_output,
            {},
            id="no-progress-status-messages",
        ),
        pytest.param(
            ["--progress=yes"],
            False,
            file_output,
            {},
            id="progress-no-status-messages",
        ),
        pytest.param(
            ["--progress=no"],
            False,
            file_output,
            {},
            id="no-progress-no-status-messages",
        ),
        pytest.param(
            ["--progress=force"],
            False,
            file_output,
            {"path": filename, "interval": PROGRESS_INTERVAL_NO_STATUS, "status": False},
            id="force-progress-no-status-messages",
        ),
    ],
    indirect=["argv", "output"],
)
def test_get_output_progress(
    monkeypatch: pytest.MonkeyPatch,
    argv: list,
    output: PlayerOutput | FileOutput,
    supports_status_messages: bool,
    expected: dict,
):
    mock_progress = Mock(return_value=sentinel.progress if expected else None)
    monkeypatch.setattr(streamlink_cli.main, "Progress", mock_progress)

    mock_console = Mock(supports_status_messages=Mock(return_value=supports_status_messages))
    monkeypatch.setattr(streamlink_cli.main, "console", mock_console)

    result = streamlink_cli.main.get_output_progress(output)
    if not expected:
        assert result is None
    else:
        assert result is sentinel.progress
        assert mock_progress.call_args_list == [call(mock_console, **expected)]
