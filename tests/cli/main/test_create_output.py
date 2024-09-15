import re
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from streamlink_cli.compat import stdout
from streamlink_cli.exceptions import StreamlinkCLIError
from streamlink_cli.main import (
    Formatter,
    build_parser,
    create_output,
    setup_args,
)
from streamlink_cli.output import FileOutput, PlayerOutput


ARGS_PLAYER_ENV = "--player-env=VAR1=abc", "--player-env=VAR2=def"


@pytest.fixture(autouse=True)
def argv(argv: list):
    parser = build_parser()
    setup_args(parser)

    return argv


@pytest.fixture(autouse=True)
def _default_stream_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.main.DEFAULT_STREAM_METADATA", {"title": "bar"})


@pytest.fixture()
def formatter():
    return Formatter(
        {
            "author": lambda: "foo",
        },
    )


@pytest.fixture()
def check_file_output(monkeypatch: pytest.MonkeyPatch):
    mock_check_file_output = Mock(side_effect=lambda path, force: FileOutput(path))
    monkeypatch.setattr("streamlink_cli.main.check_file_output", mock_check_file_output)

    return mock_check_file_output


@pytest.mark.parametrize(
    ("argv", "title"),
    [
        pytest.param(
            ["--player=mpv", "--player-args=--no-border", *ARGS_PLAYER_ENV, "URL"],
            "URL",
            id="title-default",
        ),
        pytest.param(
            ["--player=mpv", "--player-args=--no-border", *ARGS_PLAYER_ENV, "--title={author} - {title}", "URL"],
            "foo - bar",
            id="title-custom",
        ),
    ],
    indirect=["argv"],
)
def test_player_output_options(argv: list, formatter: Formatter, title: str):
    output = create_output(formatter)
    assert isinstance(output, PlayerOutput)
    assert output.playerargs.path == Path("mpv")
    assert output.playerargs.args == "--no-border"
    assert output.playerargs.title == title
    assert output.env == {"VAR1": "abc", "VAR2": "def"}


@pytest.mark.parametrize(
    ("argv", "force"),
    [
        pytest.param(["--output=foo"], False, id="no-force"),
        pytest.param(["--output=foo", "--force"], True, id="force"),
    ],
    indirect=["argv"],
)
def test_file_output(check_file_output: Mock, formatter: Formatter, argv: list, force: bool):
    output = create_output(formatter)
    assert check_file_output.call_args_list == [call(Path("foo"), force)]
    assert isinstance(output, FileOutput)
    assert output.filename == Path("foo")
    assert output.fd is None
    assert output.record is None


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--stdout"], id="--stdout"),
        pytest.param(["--output=-"], id="--output=-"),
    ],
    indirect=["argv"],
)
def test_stdout(formatter: Formatter, argv: list):
    output = create_output(formatter)
    assert isinstance(output, FileOutput)
    assert output.filename is None
    assert output.fd is stdout
    assert output.record is None


@pytest.mark.parametrize(
    ("argv", "force"),
    [
        pytest.param(["--record-and-pipe=foo"], False, id="no-force"),
        pytest.param(["--record-and-pipe=foo", "--force"], True, id="force"),
    ],
    indirect=["argv"],
)
def test_record_and_pipe(check_file_output: Mock, formatter: Formatter, argv: list, force: bool):
    output = create_output(formatter)
    assert check_file_output.call_args_list == [call(Path("foo"), force)]
    assert isinstance(output, FileOutput)
    assert output.filename is None
    assert output.fd is stdout
    assert isinstance(output.record, FileOutput)
    assert output.record.filename == Path("foo")
    assert output.record.fd is None
    assert output.record.record is None


@pytest.mark.parametrize(
    ("argv", "force", "title"),
    [
        pytest.param(
            ["--record=foo", "--player=mpv", *ARGS_PLAYER_ENV, "URL"],
            False,
            "URL",
            id="no-force-title-default",
        ),
        pytest.param(
            ["--record=foo", "--player=mpv", *ARGS_PLAYER_ENV, "--title={author} - {title}", "URL"],
            False,
            "foo - bar",
            id="title-custom",
        ),
        pytest.param(
            ["--record=foo", "--force", "--player=mpv", *ARGS_PLAYER_ENV, "URL"],
            True,
            "URL",
            id="force",
        ),
    ],
    indirect=["argv"],
)
def test_record(check_file_output: Mock, formatter: Formatter, argv: list, force: bool, title: str):
    output = create_output(formatter)
    assert check_file_output.call_args_list == [call(Path("foo"), force)]
    assert isinstance(output, PlayerOutput)
    assert output.playerargs.title == title
    assert output.env == {"VAR1": "abc", "VAR2": "def"}
    assert isinstance(output.record, FileOutput)
    assert output.record.filename == Path("foo")
    assert output.record.fd is None
    assert output.record.record is None


@pytest.mark.parametrize(
    "argv",
    [pytest.param(["--record=-", "--player=mpv", *ARGS_PLAYER_ENV, "--title={author} - {title}", "URL"])],
    indirect=["argv"],
)
def test_record_stdout(formatter: Formatter, argv: list):
    output = create_output(formatter)
    assert type(output) is PlayerOutput
    assert output.playerargs.title == "foo - bar"
    assert output.env == {"VAR1": "abc", "VAR2": "def"}
    assert type(output.record) is FileOutput
    assert output.record.filename is None
    assert output.record.fd is stdout
    assert output.record.record is None


@pytest.mark.parametrize(
    "argv",
    [pytest.param(["--record-and-pipe=foo", "--stdout"])],
    indirect=["argv"],
)
def test_record_and_other_file_output(formatter: Formatter, argv: list):
    with pytest.raises(StreamlinkCLIError) as excinfo:
        create_output(formatter)
    assert str(excinfo.value) == "Cannot use record options with other file output options."
    assert excinfo.value.code == 1


@pytest.mark.parametrize("argv", [pytest.param([], id="default-player")], indirect=["argv"])
def test_no_default_player(formatter: Formatter, argv: list):
    with pytest.raises(StreamlinkCLIError) as excinfo:
        create_output(formatter)
    assert re.search(r"^The default player \(\w+\) does not seem to be installed\.", str(excinfo.value))
    assert excinfo.value.code == 1
