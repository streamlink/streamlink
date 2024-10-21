from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from streamlink_cli.utils.player import find_default_player


# noinspection PyTestParametrized
class TestFindDefaultPlayer:
    @pytest.fixture(autouse=True)
    def _fakehome(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        home = getattr(request, "param", "")
        monkeypatch.setattr("streamlink_cli.utils.player.Path.home", lambda: home)

    @pytest.fixture(autouse=True)
    def _environ(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        for key, value in getattr(request, "param", {}).items():
            monkeypatch.setenv(key, value)

    @pytest.fixture(autouse=True)
    def which(self, request: pytest.FixtureRequest):
        return_values = getattr(request, "param", {})
        with patch("streamlink_cli.utils.player.which", side_effect=lambda path: return_values.get(path, None)) as mock_which:
            yield mock_which

    @pytest.fixture(autouse=True)
    def _assert_find_default_player(
        self,
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        which: Mock,
        lookups: list[str],
        expected: str | None,
    ):
        monkeypatch.setattr("streamlink_cli.utils.player.is_win32", "win32" in request.function.__name__)
        monkeypatch.setattr("streamlink_cli.utils.player.is_darwin", "darwin" in request.function.__name__)
        yield
        assert find_default_player() == expected
        assert which.call_args_list == [call(path) for path in lookups]

    @pytest.mark.windows_only()
    @pytest.mark.parametrize(
        "_environ",
        [
            {
                "PROGRAMFILES": "C:\\Program Files",
                "PROGRAMFILES(X86)": "C:\\Program Files (x86)",
                "PROGRAMW6432": "C:\\Program Files",
            },
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        ("which", "lookups", "expected"),
        [
            pytest.param(
                {"vlc.exe": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"},
                ["vlc.exe"],
                Path("C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"),
                id="PATH lookup success",
            ),
            pytest.param(
                {"C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe": "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"},
                [
                    "vlc.exe",
                    "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
                    "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
                ],
                Path("C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"),
                id="fallback paths lookup success",
            ),
            pytest.param(
                {},
                [
                    "vlc.exe",
                    "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
                    "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
                ],
                None,
                id="lookup failure",
            ),
        ],
        indirect=["which"],
    )
    def test_win32(self):
        pass

    @pytest.mark.windows_only()
    @pytest.mark.parametrize(
        "_environ",
        [
            {
                "PROGRAMFILES": "",
                "PROGRAMFILES(X86)": "",
                "PROGRAMW6432": "",
            },
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        ("which", "lookups", "expected"),
        [
            pytest.param(
                {"vlc.exe": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"},
                ["vlc.exe"],
                Path("C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"),
                id="PATH lookup success",
            ),
            pytest.param(
                {},
                ["vlc.exe"],
                None,
                id="no fallback paths",
            ),
        ],
        indirect=["which"],
    )
    def test_win32_no_env_vars(self):
        pass

    @pytest.mark.posix_only()
    @pytest.mark.usefixtures("_fakehome")
    @pytest.mark.parametrize("_fakehome", ["/Users/fake"], indirect=True)
    @pytest.mark.parametrize(
        ("which", "lookups", "expected"),
        [
            pytest.param(
                {"vlc": "/usr/bin/vlc"},
                ["VLC", "vlc"],
                Path("/usr/bin/vlc"),
                id="PATH lookup success",
            ),
            pytest.param(
                {"/Applications/VLC.app/Contents/MacOS/VLC": "/Applications/VLC.app/Contents/MacOS/VLC"},
                [
                    "VLC",
                    "vlc",
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                ],
                Path("/Applications/VLC.app/Contents/MacOS/VLC"),
                id="fallback paths lookup success",
            ),
            pytest.param(
                {},
                [
                    "VLC",
                    "vlc",
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                    "/Applications/VLC.app/Contents/MacOS/vlc",
                    "/Users/fake/Applications/VLC.app/Contents/MacOS/VLC",
                    "/Users/fake/Applications/VLC.app/Contents/MacOS/vlc",
                ],
                None,
                id="lookup failure",
            ),
        ],
        indirect=["which"],
    )
    def test_darwin(self):
        pass

    @pytest.mark.posix_only()
    @pytest.mark.parametrize(
        ("which", "lookups", "expected"),
        [
            pytest.param(
                {"vlc": "/usr/bin/vlc"},
                ["vlc"],
                Path("/usr/bin/vlc"),
                id="lookup success",
            ),
            pytest.param(
                {},
                ["vlc"],
                None,
                id="lookup failure",
            ),
        ],
        indirect=["which"],
    )
    def test_other(self):
        pass
