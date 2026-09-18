from __future__ import annotations

import pytest

import streamlink_cli.main


def test_parse_error(capsys: pytest.CaptureFixture[str], argv: list[str]):
    argv.append("--loglevel=doesnotexist")

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 2

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr.startswith("streamlink: error: argument -l/--loglevel: invalid choice: 'doesnotexist'")
