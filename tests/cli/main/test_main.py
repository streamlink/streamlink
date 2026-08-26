from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

import streamlink_cli.main
from streamlink_cli.exceptions import StreamlinkCLIError


@pytest.mark.parametrize(
    ("stdio", "expected"),
    [
        pytest.param({}, "foo\n", id="has-stderr"),
        pytest.param({"sys.stderr": None}, "", id="no-stderr"),
    ],
)
def test_setup_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdio: dict[str, Any],
    expected: str,
):
    monkeypatch.setattr("streamlink_cli.main.setup", Mock(side_effect=StreamlinkCLIError("foo", code=123)))
    for k, v in stdio.items():
        monkeypatch.setattr(k, v)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()

    stdout, stderr = capsys.readouterr()
    assert exc_info.value.code == 123
    assert not stdout
    assert stderr == expected
