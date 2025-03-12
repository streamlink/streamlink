from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from streamlink.exceptions import StreamlinkWarning
from streamlink_cli.output.player import (
    PlayerArgs,
    PlayerArgsMPV,
    PlayerArgsPotplayer,
    PlayerArgsVLC,
    PlayerOutput,
)


class TestPlayerArgs:
    @pytest.fixture()
    def playerargs(self, request: pytest.FixtureRequest):
        return PlayerOutput.playerargsfactory(**getattr(request, "param", {}))

    @pytest.fixture()
    def _playerargv(self, request: pytest.FixtureRequest, playerargs: PlayerArgs):
        assert playerargs.build() == getattr(request, "param", None)

    # noinspection PyTestParametrized
    @pytest.mark.usefixtures("playerargs", "_playerargv")
    @pytest.mark.parametrize(
        ("playerargs", "_playerargv"),
        [
            pytest.param(
                dict(path=Path("player")),
                ["player", "-"],
                id="Without player args",
            ),
            pytest.param(
                dict(path=Path("path to player"), args='p1 "1 2 3" p2="4 5 6" \'p3=7 8 9\' "a=\'b c\' d" \'e"f g"h\''),
                ["path to player", "p1", "1 2 3", "p2=4 5 6", "p3=7 8 9", "a='b c' d", 'e"f g"h', "-"],
                id="Player args tokenization",
            ),
            pytest.param(
                dict(path=Path("player"), args="param1 param2=value"),
                ["player", "param1", "param2=value", "-"],
                id="Implicit playerinput variable",
            ),
            pytest.param(
                dict(path=Path("player"), args="{playerinput} param1 param2=value"),
                ["player", "-", "param1", "param2=value"],
                id="Explicit playerinput variable",
            ),
            pytest.param(
                dict(path=Path("player"), args="{playerinput} param1 param2=value {playerinput}"),
                ["player", "-", "param1", "param2=value", "-"],
                id="Duplicate playerinput variable",
            ),
            pytest.param(
                dict(path=Path("player"), args="param1 {playerinput}-stdin param2"),
                ["player", "param1", "--stdin", "param2"],
                id="Combination of playerinput variable",
            ),
            pytest.param(
                dict(path=Path("player"), args="param1 param2=value {unknown}"),
                ["player", "param1", "param2=value", "{unknown}", "-"],
                id="Unknown player args variable",
            ),
            pytest.param(
                dict(path=Path("/usr/bin/player")),
                ["/usr/bin/player", "-"],
                marks=pytest.mark.posix_only,
                id="Absolute player path (POSIX)",
            ),
            pytest.param(
                dict(path=Path("C:\\path\\to\\player.exe")),
                ["C:\\path\\to\\player.exe", "-"],
                marks=pytest.mark.windows_only,
                id="Absolute player path (Windows)",
            ),
        ],
        indirect=True,
    )
    def test_argv(self):
        pass

    # noinspection PyTestParametrized
    @pytest.mark.usefixtures("playerargs", "_playerargv")
    @pytest.mark.parametrize(
        ("playerargs", "_playerargv"),
        [
            pytest.param(
                dict(path=Path("player")),
                ["player", "-"],
                id="stdin",
            ),
            pytest.param(
                dict(path=Path("player"), namedpipe=Mock(path="namedpipe")),
                ["player", "namedpipe"],
                id="namedpipe",
            ),
            pytest.param(
                dict(path=Path("player"), filename="https://localhost:65535/-._~:/?#[]@!$&'()*+,;="),
                ["player", "https://localhost:65535/-._~:/?#[]@!$&'()*+,;="],
                id="filename",
            ),
            pytest.param(
                dict(path=Path("player"), http=Mock(url="https://localhost:65535/")),
                ["player", "https://localhost:65535/"],
                id="http",
            ),
        ],
        indirect=True,
    )
    def test_input(self):
        pass

    @pytest.mark.parametrize(
        ("playerpath", "playerargsclass"),
        [
            pytest.param(
                "player",
                PlayerArgs,
                id="Unknown player",
            ),
            pytest.param(
                "vlc",
                PlayerArgsVLC,
                id="VLC",
            ),
            pytest.param(
                "vlc.exe",
                PlayerArgs,
                marks=pytest.mark.posix_only,
                id="VLC with .exe file extension (POSIX)",
            ),
            pytest.param(
                "vlc.exe",
                PlayerArgsVLC,
                marks=pytest.mark.windows_only,
                id="VLC with .exe file extension (Windows)",
            ),
            pytest.param(
                "/usr/bin/vlc",
                PlayerArgsVLC,
                marks=pytest.mark.posix_only,
                id="VLC with absolute path (POSIX)",
            ),
            pytest.param(
                "C:\\Program Files\\VideoLAN\\VLC\\vlc",
                PlayerArgsVLC,
                marks=pytest.mark.windows_only,
                id="VLC with absolute path (Windows)",
            ),
            pytest.param(
                "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
                PlayerArgsVLC,
                marks=pytest.mark.windows_only,
                id="VLC with absolute path and file extension (Windows)",
            ),
            # don't repeat path and file extension tests
            # MPV
            pytest.param(
                "mpv",
                PlayerArgsMPV,
                id="MPV",
            ),
            # Potplayer
            pytest.param(
                "potplayer",
                PlayerArgsPotplayer,
                id="Potplayer (potplayer)",
            ),
            pytest.param(
                "potplayermini",
                PlayerArgsPotplayer,
                id="Potplayer (potplayermini)",
            ),
            pytest.param(
                "potplayermini64",
                PlayerArgsPotplayer,
                id="Potplayer (potplayermini64)",
            ),
        ],
    )
    def test_knownplayer(self, playerpath: str, playerargsclass: type[PlayerArgs]):
        assert isinstance(PlayerOutput.playerargsfactory(path=Path(playerpath)), playerargsclass)

    # noinspection PyTestParametrized
    @pytest.mark.usefixtures("playerargs", "_playerargv")
    @pytest.mark.parametrize(
        ("playerargs", "_playerargv"),
        [
            pytest.param(
                dict(path=Path("vlc"), namedpipe=Mock(path="namedpipe")),
                ["vlc", "namedpipe"],
                marks=pytest.mark.posix_only,
                id="VLC named pipe (POSIX)",
            ),
            pytest.param(
                dict(path=Path("vlc"), namedpipe=Mock(path="namedpipe")),
                ["vlc", "stream://\\namedpipe"],
                marks=pytest.mark.windows_only,
                id="VLC named pipe (Windows)",
            ),
            pytest.param(
                dict(path=Path("mpv"), namedpipe=Mock(path="namedpipe")),
                ["mpv", "namedpipe"],
                marks=pytest.mark.posix_only,
                id="MPV named pipe (POSIX)",
            ),
            pytest.param(
                dict(path=Path("mpv"), namedpipe=Mock(path="namedpipe")),
                ["mpv", "file://namedpipe"],
                marks=pytest.mark.windows_only,
                id="MPV named pipe (Windows)",
            ),
        ],
        indirect=True,
    )
    def test_knownplayer_input(self):
        pass

    # noinspection PyTestParametrized
    @pytest.mark.usefixtures("playerargs", "_playerargv")
    @pytest.mark.parametrize(
        ("playerargs", "_playerargv"),
        [
            pytest.param(
                dict(path=Path("player"), title="foo bar"),
                ["player", "-"],
                id="No title on unknown player",
            ),
            pytest.param(
                dict(path=Path("vlc"), title="foo bar: $a - $t"),
                ["vlc", "--input-title-format", "foo bar: $$a - $$t", "-"],
                id="VLC title",
            ),
            pytest.param(
                dict(path=Path("mpv"), title="foo bar"),
                ["mpv", "--force-media-title=foo bar", "-"],
                id="MPV title",
            ),
            pytest.param(
                dict(path=Path("potplayer"), title="foo bar"),
                ["potplayer", "-"],
                id="Potplayer title (stdin - no title)",
            ),
            pytest.param(
                dict(path=Path("potplayer"), title="foo bar", namedpipe=Mock(path="namedpipe")),
                ["potplayer", "namedpipe\\foo bar"],
                id="Potplayer title (namedpipe)",
            ),
            pytest.param(
                dict(path=Path("vlc"), args="param1 {playertitleargs} param2", title="foo bar"),
                ["vlc", "param1", "--input-title-format", "foo bar", "param2", "-"],
                id="Explicit playertitleargs variable",
            ),
            pytest.param(
                dict(path=Path("vlc"), args="param1{playertitleargs}param2", title="foo bar"),
                ["vlc", "param1--input-title-format", "foo barparam2", "-"],
                id="Explicit playertitleargs variable with improper usage (correct tokenization)",
            ),
        ],
        indirect=True,
    )
    def test_title(self):
        pass


# TODO: refactor PlayerOutput and write proper tests
class TestPlayerOutput:
    @pytest.fixture(autouse=True)
    def _os_environ(self, os_environ: dict[str, str]):
        os_environ["FAKE"] = "ENVIRONMENT"
        yield
        assert sorted(os_environ.keys()) == ["FAKE"], "Doesn't pollute the os.environ dict with custom env vars"

    @pytest.fixture()
    def playeroutput(self, request: pytest.FixtureRequest):
        with patch("streamlink_cli.output.player.sleep"):
            playeroutput = PlayerOutput(**getattr(request, "param", {}))
            yield playeroutput
            playeroutput.close()

    @pytest.fixture()
    def mock_which(self, request: pytest.FixtureRequest, playeroutput: PlayerOutput):
        with patch("streamlink_cli.output.player.which", return_value=getattr(request, "param", None)) as mock_which:
            yield mock_which

    @pytest.fixture()
    def mock_popen(self, playeroutput: PlayerOutput):
        with (
            patch("streamlink_cli.output.player.sleep"),
            patch("subprocess.Popen", return_value=Mock(poll=Mock(side_effect=Mock(return_value=None)))) as mock_popen,
        ):
            yield mock_popen

    @pytest.mark.parametrize(
        ("playeroutput", "mock_which", "args", "env", "logmessage"),
        [
            pytest.param(
                {"path": Path("player"), "args": "param1 param2", "call": False},
                "/resolved/player",
                ["/resolved/player", "param1", "param2", "-"],
                {"FAKE": "ENVIRONMENT"},
                "Opening subprocess: ['/resolved/player', 'param1', 'param2', '-']",
                id="Without custom env vars",
            ),
            pytest.param(
                {"path": Path("player"), "args": "param1 param2", "env": [("VAR1", "abc"), ("VAR2", "def")], "call": False},
                "/resolved/player",
                ["/resolved/player", "param1", "param2", "-"],
                {"FAKE": "ENVIRONMENT", "VAR1": "abc", "VAR2": "def"},
                "Opening subprocess: ['/resolved/player', 'param1', 'param2', '-'], env: {'VAR1': 'abc', 'VAR2': 'def'}",
                id="With custom env vars",
            ),
        ],
        indirect=["playeroutput", "mock_which"],
    )
    def test_open_popen_parameters(
        self,
        caplog: pytest.LogCaptureFixture,
        playeroutput: PlayerOutput,
        mock_which: Mock,
        mock_popen: Mock,
        args: Sequence[str],
        env: Mapping[str, str],
        logmessage: str,
    ):
        caplog.set_level(1, "streamlink")

        assert getattr(playeroutput, "player", None) is None

        playeroutput.open()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.cli.output", "debug", logmessage),
        ]
        assert mock_which.call_args_list == [call("player")]
        assert mock_popen.call_args_list == [
            call(
                args,
                bufsize=0,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ),
        ]
        assert playeroutput.player is not None
        assert not playeroutput.player.terminate.called  # type: ignore

        playeroutput.close()
        assert playeroutput.player.terminate.call_count == 1  # type: ignore

    @pytest.mark.parametrize(
        ("playeroutput", "mock_which", "expected", "warns"),
        [
            pytest.param(
                dict(path=Path("foo")),
                "foo",
                nullcontext(),
                False,
                id="Player found",
            ),
            pytest.param(
                dict(path=Path("foo")),
                None,
                pytest.raises(FileNotFoundError, match=r"^Player executable not found$"),
                False,
                id="Player not found",
            ),
            pytest.param(
                dict(path=Path('"foo bar"')),
                None,
                pytest.raises(FileNotFoundError, match=r"^Player executable not found$"),
                True,
                id="Player not found with quotation warning",
            ),
        ],
        indirect=["playeroutput", "mock_which"],
    )
    def test_open_error(
        self,
        recwarn: pytest.WarningsRecorder,
        playeroutput: PlayerOutput,
        mock_which: Mock,
        mock_popen: Mock,
        expected: AbstractContextManager,
        warns: bool,
    ):
        with expected:
            playeroutput.open()
        assert any(record.category is StreamlinkWarning for record in recwarn.list) is warns
