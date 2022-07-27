import os
import tempfile
from pathlib import Path
from typing import List

from streamlink.compat import is_darwin, is_win32
from streamlink_cli.compat import DeprecatedPath


PLAYER_ARGS_INPUT_DEFAULT = "playerinput"
PLAYER_ARGS_INPUT_FALLBACK = "filename"

DEFAULT_STREAM_METADATA = {
    "id": "Unknown ID",
    "title": "Unknown Title",
    "author": "Unknown Author",
    "category": "No Category",
    "game": "No Game/Category"
}
# these are the players that streamlink knows how to set the window title for with `--title`.
# key names are used in help text
SUPPORTED_PLAYERS = {
    # name: possible binary names (linux/mac and windows)
    "vlc": ["vlc", "vlc.exe"],
    "mpv": ["mpv", "mpv.exe"],
    "potplayer": ["potplayer", "potplayermini64.exe", "potplayermini.exe"]
}

CONFIG_FILES: List[Path]
PLUGIN_DIRS: List[Path]
LOG_DIR: Path

if is_win32:
    APPDATA = Path(os.environ.get("APPDATA") or Path.home() / "AppData")
    CONFIG_FILES = [
        APPDATA / "streamlink" / "config",
        DeprecatedPath(APPDATA / "streamlink" / "streamlinkrc")
    ]
    PLUGIN_DIRS = [
        APPDATA / "streamlink" / "plugins"
    ]
    LOG_DIR = Path(tempfile.gettempdir()) / "streamlink" / "logs"
elif is_darwin:
    XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    CONFIG_FILES = [
        Path.home() / "Library" / "Application Support" / "streamlink" / "config",
        DeprecatedPath(XDG_CONFIG_HOME / "streamlink" / "config"),
        DeprecatedPath(Path.home() / ".streamlinkrc")
    ]
    PLUGIN_DIRS = [
        Path.home() / "Library" / "Application Support" / "streamlink" / "plugins",
        DeprecatedPath(XDG_CONFIG_HOME / "streamlink" / "plugins")
    ]
    LOG_DIR = DeprecatedPath(Path.home() / "Library" / "Logs" / "streamlink")
else:
    XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
    CONFIG_FILES = [
        XDG_CONFIG_HOME / "streamlink" / "config",
        DeprecatedPath(Path.home() / ".streamlinkrc")
    ]
    PLUGIN_DIRS = [
        XDG_DATA_HOME / "streamlink" / "plugins",
        DeprecatedPath(XDG_CONFIG_HOME / "streamlink" / "plugins")
    ]
    LOG_DIR = XDG_STATE_HOME / "streamlink" / "logs"

STREAM_SYNONYMS = ["best", "worst", "best-unfiltered", "worst-unfiltered"]
STREAM_PASSTHROUGH = ["hls", "http"]

__all__ = [
    "PLAYER_ARGS_INPUT_DEFAULT", "PLAYER_ARGS_INPUT_FALLBACK",
    "DEFAULT_STREAM_METADATA", "SUPPORTED_PLAYERS",
    "CONFIG_FILES", "PLUGIN_DIRS", "LOG_DIR", "STREAM_SYNONYMS", "STREAM_PASSTHROUGH"
]
