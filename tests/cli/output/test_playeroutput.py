from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from streamlink_cli.output import PlayerOutput


@pytest.fixture()
def playeroutput(request: pytest.FixtureRequest):
    with patch("streamlink_cli.output.player.sleep"):
        playeroutput = PlayerOutput(**getattr(request, "param", {}))
        yield playeroutput
        playeroutput.close()


@pytest.fixture()
def mock_popen(playeroutput: PlayerOutput):
    mock_popen = Mock(return_value=Mock(poll=Mock(side_effect=Mock(return_value=None))))
    with patch("streamlink_cli.output.player.sleep"), \
         patch("subprocess.Popen", mock_popen):
        yield mock_popen


@pytest.mark.parametrize(("playeroutput", "expected"), [
    pytest.param(
        dict(path=Path("vlc"), title="foo bar"),
        ["vlc", "--input-title-format", "foo bar", "-"],
        id="VLC title",
    ),
    pytest.param(
        dict(path=Path("mpv"), title="foo bar"),
        ["mpv", "--force-media-title=foo bar", "-"],
        id="MPV title",
    ),
], indirect=["playeroutput"])
def test_playeroutput_title(mock_popen: Mock, playeroutput: PlayerOutput, expected):
    playeroutput.open()
    assert mock_popen.call_args_list == [
        call(expected, bufsize=0, stdout=playeroutput.stdout, stderr=playeroutput.stderr, stdin=playeroutput.stdin),
    ]


@pytest.mark.parametrize(("playeroutput", "expected"), [
    pytest.param(
        dict(path=Path("foo")),
        ["foo", "-"],
        id="No playerinput variable",
    ),
    pytest.param(
        dict(path=Path("foo"), args="--bar"),
        ["foo", "--bar", "-"],
        id="Implicit playerinput variable",
    ),
    pytest.param(
        dict(path=Path("foo"), args="--bar {playerinput}"),
        ["foo", "--bar", "-"],
        id="Explicit playerinput variable",
    ),
    pytest.param(
        dict(path=Path("foo"), args="--bar {filename}"),
        ["foo", "--bar", "-"],
        id="Fallback playerinput variable",
    ),
    pytest.param(
        dict(path=Path("foo"), args="--bar {playerinput} {filename}"),
        ["foo", "--bar", "-", "-"],
        id="Fallback duplicate playerinput variable",
    ),
    pytest.param(
        dict(path=Path("foo"), args="--bar {qux}"),
        ["foo", "--bar", "{qux}", "-"],
        id="Unknown variable",
    ),
], indirect=["playeroutput"])
def test_playeroutput_args(playeroutput: PlayerOutput, expected):
    args = playeroutput._create_arguments()
    assert args == expected
