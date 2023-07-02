from os import environ
from pathlib import Path
from shutil import which
from typing import Iterable, Optional

from streamlink.compat import is_darwin, is_win32


def _resolve_executable(paths: Iterable[Path], *exes: str) -> Optional[Path]:
    for exe in exes:
        resolved = which(exe)
        if resolved:
            return Path(resolved).resolve()

    checked = set()
    for path in paths:
        for exe in exes:
            fullpath = str(path / exe)
            if fullpath in checked:
                continue
            checked.add(fullpath)
            resolved = which(fullpath)
            if resolved:
                return Path(resolved).resolve()

    return None


def _find_default_player_win32() -> Optional[Path]:
    envvars = "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"
    subpath = Path() / "VideoLAN" / "VLC"

    return _resolve_executable(
        (
            Path(p) / subpath
            for p in (environ.get(envvar, None) for envvar in envvars)
            if p
        ),
        "vlc.exe",
    )


def _find_default_player_darwin() -> Optional[Path]:
    subpath = Path() / "Applications" / "VLC.app" / "Contents" / "MacOS"

    return _resolve_executable(
        [
            Path("/") / subpath,
            Path.home() / subpath,
        ],
        "VLC",
        "vlc",
    )


def _find_default_player_other() -> Optional[Path]:
    return _resolve_executable(
        [],
        "vlc",
    )


def find_default_player() -> Optional[Path]:
    if is_win32:
        return _find_default_player_win32()
    elif is_darwin:
        return _find_default_player_darwin()
    else:
        return _find_default_player_other()
