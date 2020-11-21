import os

from streamlink_cli.compat import is_win32

PLAYER_ARGS_INPUT_DEFAULT = "playerinput"
PLAYER_ARGS_INPUT_FALLBACK = "filename"

DEFAULT_STREAM_METADATA = {
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

if is_win32:
    APPDATA = os.environ["APPDATA"]
    CONFIG_FILES = [os.path.join(APPDATA, "streamlink", "streamlinkrc")]
    PLUGINS_DIR = os.path.join(APPDATA, "streamlink", "plugins")
else:
    XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    CONFIG_FILES = [
        os.path.expanduser(XDG_CONFIG_HOME + "/streamlink/config"),
        os.path.expanduser("~/.streamlinkrc")
    ]
    PLUGINS_DIR = os.path.expanduser(XDG_CONFIG_HOME + "/streamlink/plugins")

STREAM_SYNONYMS = ["best", "worst", "best-unfiltered", "worst-unfiltered"]
STREAM_PASSTHROUGH = ["hls", "http", "rtmp"]

__all__ = [
    "PLAYER_ARGS_INPUT_DEFAULT", "PLAYER_ARGS_INPUT_FALLBACK",
    "DEFAULT_STREAM_METADATA", "SUPPORTED_PLAYERS",
    "CONFIG_FILES", "PLUGINS_DIR", "STREAM_SYNONYMS", "STREAM_PASSTHROUGH"
]
