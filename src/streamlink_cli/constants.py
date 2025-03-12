from __future__ import annotations

import os
import tempfile
from pathlib import Path

from streamlink.compat import is_darwin, is_win32


DEFAULT_STREAM_METADATA = {
    "id": "Unknown ID",
    "title": "Unknown Title",
    "author": "Unknown Author",
    "category": "No Category",
    "game": "No Game/Category",
}

CONFIG_FILES: list[Path]
PLUGIN_DIRS: list[Path]
LOG_DIR: Path

if is_win32:
    APPDATA = Path(os.environ.get("APPDATA") or Path.home() / "AppData")
    CONFIG_FILES = [
        APPDATA / "streamlink" / "config",
    ]
    PLUGIN_DIRS = [
        APPDATA / "streamlink" / "plugins",
    ]
    LOG_DIR = Path(tempfile.gettempdir()) / "streamlink" / "logs"
elif is_darwin:
    XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    CONFIG_FILES = [
        Path.home() / "Library" / "Application Support" / "streamlink" / "config",
    ]
    PLUGIN_DIRS = [
        Path.home() / "Library" / "Application Support" / "streamlink" / "plugins",
    ]
    LOG_DIR = Path.home() / "Library" / "Logs" / "streamlink"
else:
    XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
    CONFIG_FILES = [
        XDG_CONFIG_HOME / "streamlink" / "config",
    ]
    PLUGIN_DIRS = [
        XDG_DATA_HOME / "streamlink" / "plugins",
    ]
    LOG_DIR = XDG_STATE_HOME / "streamlink" / "logs"

STREAM_SYNONYMS = ["best", "worst", "best-unfiltered", "worst-unfiltered"]
STREAM_PASSTHROUGH = ["hls", "http"]


__all__ = [
    "CONFIG_FILES",
    "DEFAULT_STREAM_METADATA",
    "LOG_DIR",
    "PLUGIN_DIRS",
    "STREAM_PASSTHROUGH",
    "STREAM_SYNONYMS",
]
