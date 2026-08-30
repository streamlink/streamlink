from unittest.mock import Mock

import pytest

import streamlink_cli.main


@pytest.mark.parametrize(
    ("argv", "latest", "aborted", "exit_code"),
    [
        pytest.param(
            ["--version-check"],
            True,
            True,
            130,
            id="aborted",
        ),
        pytest.param(
            ["--version-check"],
            True,
            False,
            0,
            id="latest",
        ),
        pytest.param(
            ["--version-check"],
            False,
            False,
            1,
            id="outdated",
        ),
        pytest.param(
            ["--auto-version-check=True"],
            True,
            False,
            0,
            id="auto-latest",
        ),
        pytest.param(
            ["--auto-version-check=True"],
            False,
            False,
            0,
            id="auto-outdated",
        ),
    ],
    indirect=["argv"],
)
def test_version_check(monkeypatch: pytest.MonkeyPatch, argv: list, latest: bool, aborted: bool, exit_code: int):
    mock_check_version = Mock(return_value=latest, side_effect=KeyboardInterrupt if aborted else None)
    monkeypatch.setattr("streamlink_cli.main.check_version", mock_check_version)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == exit_code
    assert mock_check_version.call_count == 1
