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
        dict(cmd="mpv", title="foo bar"),
        ["mpv", "--force-media-title=foo bar", "-"],
        marks=pytest.mark.posix_only,
        id="MPV title POSIX",
    ),
    pytest.param(
        {"cmd": "mpv.exe", "title": "foo bar"},
        "mpv.exe \"--force-media-title=foo bar\" -",
        marks=pytest.mark.windows_only,
        id="MPV title Windows",
    ),
    pytest.param(
        {"cmd": "vlc", "title": "foo bar"},
        ["vlc", "--input-title-format", "foo bar", "-"],
        marks=pytest.mark.posix_only,
        id="VLC title POSIX",
    ),
    pytest.param(
        {"cmd": "vlc.exe", "title": "foo bar"},
        "vlc.exe --input-title-format \"foo bar\" -",
        marks=pytest.mark.windows_only,
        id="VLC title Windows",
    ),
], indirect=["playeroutput"])
def test_playeroutput(mock_popen: Mock, playeroutput: PlayerOutput, expected):
    playeroutput.open()
    assert mock_popen.call_args_list == [
        call(expected, bufsize=0, stdout=playeroutput.stdout, stderr=playeroutput.stderr, stdin=playeroutput.stdin),
    ]


@pytest.mark.parametrize(("playeroutput", "expected"), [
    pytest.param(
        dict(cmd="foo"),
        ["foo", "-"],
        marks=pytest.mark.posix_only,
        id="None POSIX",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar"),
        ["foo", "--bar", "-"],
        marks=pytest.mark.posix_only,
        id="Implicit POSIX",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {playerinput}"),
        ["foo", "--bar", "-"],
        marks=pytest.mark.posix_only,
        id="Explicit POSIX",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {filename}"),
        ["foo", "--bar", "-"],
        marks=pytest.mark.posix_only,
        id="Fallback POSIX",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {playerinput} {filename}"),
        ["foo", "--bar", "-", "-"],
        marks=pytest.mark.posix_only,
        id="Fallback duplicate POSIX",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {qux}"),
        ["foo", "--bar", "{qux}", "-"],
        marks=pytest.mark.posix_only,
        id="Unknown POSIX",
    ),
    pytest.param(
        dict(cmd="foo"),
        "foo -",
        marks=pytest.mark.windows_only,
        id="None Windows",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar"),
        "foo --bar -",
        marks=pytest.mark.windows_only,
        id="Implicit Windows",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {playerinput}"),
        "foo --bar -",
        marks=pytest.mark.windows_only,
        id="Explicit Windows",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {filename}"),
        "foo --bar -",
        marks=pytest.mark.windows_only,
        id="Fallback Windows",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {playerinput} {filename}"),
        "foo --bar - -",
        marks=pytest.mark.windows_only,
        id="Fallback duplicate Windows",
    ),
    pytest.param(
        dict(cmd="foo", args="--bar {qux}"),
        "foo --bar {qux} -",
        marks=pytest.mark.windows_only,
        id="Unknown Windows",
    ),
], indirect=["playeroutput"])
def test_playeroutput_args(playeroutput: PlayerOutput, expected):
    args = playeroutput._create_arguments()
    assert args == expected
