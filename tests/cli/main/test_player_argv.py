from pathlib import Path
from unittest.mock import ANY, Mock, call

import pytest

import streamlink_cli.main
import tests
from streamlink import Streamlink


@pytest.fixture(autouse=True)
def session(session: Streamlink):
    session.plugins.load_path(Path(tests.__path__[0]) / "plugin")

    return session


@pytest.fixture(autouse=True)
def _player_setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.output.player.which", Mock(side_effect=lambda path: path))
    monkeypatch.setattr("streamlink_cli.output.player.sleep", Mock())


@pytest.fixture(autouse=True)
def mock_subprocess(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    param = getattr(request, "param", {})
    popen = param.get("popen", [])
    call_ = param.get("call", [])

    mock_call = Mock()
    monkeypatch.setattr("streamlink_cli.output.player.subprocess.call", mock_call)

    mock_popen = Mock()
    mock_popen.return_value = Mock(poll=Mock(side_effect=[None, 0]))
    monkeypatch.setattr("streamlink_cli.output.player.subprocess.Popen", mock_popen)

    yield

    if popen:
        assert mock_popen.call_args_list == [call(popen, env=ANY, bufsize=ANY, stdin=ANY, stdout=ANY, stderr=ANY)]
        assert mock_call.call_args_list == []
    else:
        assert mock_popen.call_args_list == []
        assert mock_call.call_args_list == [call(call_, env=ANY, stdout=ANY, stderr=ANY)]


@pytest.fixture(autouse=True)
def _test(argv: list, mock_subprocess: Mock):
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 0


@pytest.mark.parametrize(
    ("argv", "mock_subprocess"),
    [
        pytest.param(
            ["--player=player", "http://test.se", "test"],
            {"popen": ["player", "-"]},
            id="player-stdin",
        ),
        pytest.param(
            ["-p", "player", "-a", "-v {playerinput}", "http://test.se", "test"],
            {"popen": ["player", "-v", "-"]},
            id="player-args-single-hyphen-ghissue-971",
        ),
        pytest.param(
            ["-p", "player", "-a", '--input-title-format "foo \\"bar\\""', "--player-passthrough=hls", "test.se", "hls"],
            {"call": ["player", "--input-title-format", 'foo "bar"', "http://test.se/playlist.m3u8"]},
            id="player-passthrough",
        ),
    ],
    indirect=["argv", "mock_subprocess"],
)
def test_player_argv(argv: list, mock_subprocess: Mock):
    pass


@pytest.mark.posix_only()
@pytest.mark.parametrize(
    ("argv", "mock_subprocess"),
    [
        pytest.param(
            ["-p", "/usr/bin/vlc", "http://test.se", "test"],
            {"popen": ["/usr/bin/vlc", "--input-title-format", "http://test.se", "-"]},
            id="vlc-default",
        ),
        pytest.param(
            ["-p", "/usr/bin/vlc", "--title", "{title} - {author} - {category}", "http://test.se", "test"],
            {"popen": ["/usr/bin/vlc", "--input-title-format", "Test Title - Tѥst Āuƭhǿr - No Category", "-"]},
            id="vlc-custom",
        ),
        pytest.param(
            ["-p", "/Applications/VLC/vlc", "-a", "--play-and-exit", "http://test.se", "test"],
            {"popen": ["/Applications/VLC/vlc", "--input-title-format", "http://test.se", "--play-and-exit", "-"]},
            id="vlc-custom-with-args",
        ),
        pytest.param(
            ["-p", "/usr/bin/mpv", "--title", "{title}", "http://test.se", "test"],
            {"popen": ["/usr/bin/mpv", "--force-media-title=Test Title", "-"]},
            id="mpv-default",
        ),
    ],
    indirect=["argv", "mock_subprocess"],
)
def test_player_title_posix(argv: list, mock_subprocess: Mock):
    pass


@pytest.mark.windows_only()
@pytest.mark.parametrize(
    ("argv", "mock_subprocess"),
    [
        pytest.param(
            ["-p", "Z:\\VideoLAN\\vlc.exe", "http://test.se", "test"],
            {"popen": ["Z:\\VideoLAN\\vlc.exe", "--input-title-format", "http://test.se", "-"]},
            id="vlc-default",
        ),
        pytest.param(
            ["-p", "Z:\\VideoLAN\\vlc.exe", "--title", "{title} - {author} - {category}", "http://test.se", "test"],
            {"popen": ["Z:\\VideoLAN\\vlc.exe", "--input-title-format", "Test Title - Tѥst Āuƭhǿr - No Category", "-"]},
            id="vlc-custom",
        ),
        pytest.param(
            ["-p", "Z:\\VideoLAN\\vlc.exe", "-a", "--play-and-exit", "http://test.se", "test"],
            {"popen": ["Z:\\VideoLAN\\vlc.exe", "--input-title-format", "http://test.se", "--play-and-exit", "-"]},
            id="vlc-custom-with-args",
        ),
        pytest.param(
            ["-p", "Z:\\PotPlayerMini64.exe", "--player-passthrough=hls", "http://test.se/stream", "hls"],
            {"call": ["Z:\\PotPlayerMini64.exe", "http://test.se/playlist.m3u8\\http://test.se/stream"]},
            id="potplayer-passthrough-default",
        ),
        pytest.param(
            ["-p", "Z:\\PotPlayerMini64.exe", "--player-passthrough=hls", "--title", "{title}", "http://test.se/stream", "hls"],
            {"call": ["Z:\\PotPlayerMini64.exe", "http://test.se/playlist.m3u8\\Test Title"]},
            id="potplayer-passthrough-custom",
        ),
    ],
    indirect=["argv", "mock_subprocess"],
)
def test_player_title_windows(argv: list, mock_subprocess: Mock):
    pass
