from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import streamlink_cli.main


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(
            ["--http-cookies-file", "doesnotexist"],
            id="http-cookies-file",
        ),
    ],
    indirect=["argv"],
)
def test_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str]):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 1
    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == f"Error while loading cookies from file: '{tmp_path / 'doesnotexist'}' is not a valid cookies file path\n"
