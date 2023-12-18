from contextlib import nullcontext
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import pytest

from streamlink_cli.main import check_file_output
from streamlink_cli.output.file import FileOutput


if TYPE_CHECKING:  # pragma: no cover
    _BasePath = PurePosixPath
else:
    _BasePath = type(PurePosixPath())


# Fake PurePosixPath, with a fake is_file() method which gets mocked in the path fixture down below:
# Can't override/extend the constructor with custom args/kwargs due to major code changes in py310
# which are incompatible with older versions of pathlib.PurePath
class _FakePath(_BasePath):
    @staticmethod
    def is_file():  # pragma: no cover
        return False


@pytest.fixture(autouse=True)
def _caplog(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink.cli")


@pytest.fixture(autouse=True)
def path(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    param = getattr(request, "param", {})
    file = param.get("file", "file")
    realpath = param.get("realpath", "/path/to/file")
    exists = param.get("exists", False)

    monkeypatch.setattr("os.path.realpath", Mock(return_value=realpath))
    monkeypatch.setattr("streamlink_cli.main.Path", _FakePath)
    monkeypatch.setattr(_FakePath, "is_file", Mock(return_value=exists))

    return Path(file)


@pytest.fixture()
def prompt(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    param = getattr(request, "param", {})
    isatty = param.get("isatty", True)
    ask = param.get("ask", "y")

    prompt = Mock(return_value=ask)
    monkeypatch.setattr("sys.stdin.isatty", Mock(return_value=isatty))
    monkeypatch.setattr("streamlink_cli.main.console", Mock(ask=prompt))

    return prompt


@pytest.mark.parametrize(("path", "force", "prompt", "exits", "log"), [
    pytest.param(
        {"exists": False},
        False,
        {},
        nullcontext(),
        [
            ("streamlink.cli", "info", "Writing output to\n/path/to/file"),
            ("streamlink.cli", "debug", "Checking file output"),
        ],
        id="file does not exist",
    ),
    pytest.param(
        {"exists": True},
        True,
        {},
        nullcontext(),
        [
            ("streamlink.cli", "info", "Writing output to\n/path/to/file"),
            ("streamlink.cli", "debug", "Checking file output"),
        ],
        id="file exists, force",
    ),
    pytest.param(
        {"exists": True},
        False,
        {"isatty": False},
        pytest.raises(SystemExit),
        [
            ("streamlink.cli", "info", "Writing output to\n/path/to/file"),
            ("streamlink.cli", "debug", "Checking file output"),
            ("streamlink.cli", "error", "File file already exists, use --force to overwrite it."),
        ],
        id="file exists, no TTY",
    ),
], indirect=["path", "prompt"])
def test_exists(
    caplog: pytest.LogCaptureFixture,
    path: Path,
    force: bool,
    prompt: Mock,
    exits: nullcontext,
    log: list,
):
    with exits:
        output = check_file_output(path, force)
        assert isinstance(output, FileOutput)
        assert output.filename == PurePosixPath("/path/to/file")

    assert [(record.name, record.levelname, record.message) for record in caplog.records] == log
    assert prompt.call_args_list == []


@pytest.mark.parametrize("path", [pytest.param({"exists": True}, id="")], indirect=True)
@pytest.mark.parametrize(("prompt", "exits"), [
    pytest.param(
        {"ask": "y"},
        nullcontext(),
        id="yes",
    ),
    pytest.param(
        {"ask": "n"},
        pytest.raises(SystemExit),
        id="no",
    ),
    pytest.param(
        {"ask": None},
        pytest.raises(SystemExit),
        id="error",
    ),
], indirect=["prompt"])
def test_prompt(
    caplog: pytest.LogCaptureFixture,
    path: Path,
    prompt: Mock,
    exits: nullcontext,
):
    with exits:
        output = check_file_output(path, False)
        assert isinstance(output, FileOutput)
        assert output.filename == PurePosixPath("/path/to/file")

    assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
        ("streamlink.cli", "info", "Writing output to\n/path/to/file"),
        ("streamlink.cli", "debug", "Checking file output"),
    ]
    assert prompt.call_args_list == [call("File file already exists! Overwrite it? [y/N] ")]
