import os
import tempfile

from streamlink_cli.compat import is_win32

DEFAULT_PLAYER_ARGUMENTS = "{filename}"
PLAYER_ARGS_INPUT_DEFAULT = "playerinput"
PLAYER_ARGS_INPUT_FALLBACK = "filename"

DEFAULT_STREAM_METADATA = {
    "id": u"Unknown ID",
    "title": u"Unknown Title",
    "author": u"Unknown Author",
    "category": u"No Category",
    "game": u"No Game/Category"
}
# these are the players that streamlink knows how to set the window title for with `--title`.
# key names are used in help text
SUPPORTED_PLAYERS = {
    # name: possible binary names (linux/mac and windows)
    "vlc": ["vlc", "vlc.exe"],
    "mpv": ["mpv", "mpv.exe"],
    "potplayer": ["potplayer", "potplayermini64.exe", "potplayermini.exe"]
}

if is_win32:
    APPDATA = os.environ["APPDATA"]
    CONFIG_FILES = [os.path.join(APPDATA, "streamlink", "streamlinkrc")]
    PLUGINS_DIR = os.path.join(APPDATA, "streamlink", "plugins")
    LOG_DIR = os.path.join(tempfile.gettempdir(), "streamlink", "logs")
else:
    XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    XDG_STATE_HOME = os.environ.get("XDG_STATE_HOME", "~/.local/state")
    CONFIG_FILES = [
        os.path.join(os.path.expanduser(XDG_CONFIG_HOME), "streamlink", "config"),
        os.path.expanduser("~/.streamlinkrc")
    ]
    PLUGINS_DIR = os.path.join(os.path.expanduser(XDG_CONFIG_HOME), "streamlink", "plugins")
    LOG_DIR = os.path.join(os.path.expanduser(XDG_STATE_HOME), "streamlink", "logs")

STREAM_SYNONYMS = ["best", "worst", "best-unfiltered", "worst-unfiltered"]
STREAM_PASSTHROUGH = ["hls", "http", "rtmp"]

__all__ = [
    "PLAYER_ARGS_INPUT_DEFAULT", "PLAYER_ARGS_INPUT_FALLBACK",
    "DEFAULT_STREAM_METADATA", "SUPPORTED_PLAYERS",
    "CONFIG_FILES", "PLUGINS_DIR", "LOG_DIR", "STREAM_SYNONYMS", "STREAM_PASSTHROUGH"
]
