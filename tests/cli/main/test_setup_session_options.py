from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import streamlink_cli.main


if TYPE_CHECKING:
    from pathlib import Path

    from streamlink.session import Streamlink


def test_setup_session_options(monkeypatch: pytest.MonkeyPatch, session: Streamlink, argv: list[str]):
    argv.extend(["--quiet"])

    mock_setup_session_options = Mock()
    monkeypatch.setattr("streamlink_cli.main.setup_session_options", mock_setup_session_options)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 0

    assert mock_setup_session_options.call_count == 1
    expected_session, expected_namespace = mock_setup_session_options.call_args_list[0].args
    assert expected_session is session
    assert expected_namespace is streamlink_cli.main.args
    assert expected_namespace.quiet


def test_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str]):
    argv.extend(["--http-cookies-file", "doesnotexist"])

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 1
    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == f"Error while loading cookies from file: '{tmp_path / 'doesnotexist'}' is not a valid cookies file path\n"
