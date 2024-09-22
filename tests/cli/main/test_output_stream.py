from io import BytesIO
from unittest.mock import Mock, call

import pytest

import streamlink_cli.main
from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.main import build_parser, setup_args


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
def output(monkeypatch: pytest.MonkeyPatch):
    output = Mock()
    monkeypatch.setattr(streamlink_cli.main, "output", output)
    monkeypatch.setattr(streamlink_cli.main, "create_output", Mock(return_value=output))

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


@pytest.mark.parametrize(
    ("argv", "isatty", "expected"),
    [
        pytest.param(["--retry-open=1", "--progress=yes"], True, True, id="progress-tty"),
        pytest.param(["--retry-open=1", "--progress=no"], True, False, id="no-progress-tty"),
        pytest.param(["--retry-open=1", "--progress=yes"], False, False, id="progress-no-tty"),
        pytest.param(["--retry-open=1", "--progress=no"], False, False, id="no-progress-no-tty"),
        pytest.param(["--retry-open=1", "--progress=force"], False, True, id="force-progress-no-tty"),
    ],
    indirect=["argv"],
)
def test_show_progress(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    argv: list,
    output: Mock,
    stream: Stream,
    isatty: bool,
    expected: bool,
):
    streamio = BytesIO(b"0" * 8192 * 2)
    monkeypatch.setattr(stream, "open", Mock(return_value=streamio))
    monkeypatch.setattr("sys.stderr.isatty", Mock(return_value=isatty))

    mock_streamrunner = Mock()
    monkeypatch.setattr(streamlink_cli.main, "StreamRunner", mock_streamrunner)

    assert streamlink_cli.main.output_stream(stream, Mock())

    assert [(record.levelname, record.module, record.message) for record in caplog.records] == [
        ("debug", "main", "Pre-buffering 8192 bytes"),
        ("debug", "main", "Writing stream to output"),
    ]
    assert mock_streamrunner.call_args_list == [call(streamio, output, show_progress=expected)]
