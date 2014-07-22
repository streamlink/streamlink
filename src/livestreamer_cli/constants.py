import os

from livestreamer import __version__ as LIVESTREAMER_VERSION

from .compat import is_win32

DEFAULT_PLAYER_ARGUMENTS = "{filename}"

if is_win32:
    APPDATA = os.environ["APPDATA"]
    CONFIG_FILES = [os.path.join(APPDATA, "livestreamer", "livestreamerrc")]
    PLUGINS_DIR = os.path.join(APPDATA, "livestreamer", "plugins")
else:
    XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    CONFIG_FILES = [
        os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/config"),
        os.path.expanduser("~/.livestreamerrc")
    ]
    PLUGINS_DIR = os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/plugins")

STREAM_SYNONYMS = ["best", "worst"]
STREAM_PASSTHROUGH = ["hls", "http", "rtmp"]

__all__ = [
    "CONFIG_FILES", "DEFAULT_PLAYER_ARGUMENTS", "LIVESTREAMER_VERSION",
    "PLUGINS_DIR", "STREAM_SYNONYMS", "STREAM_PASSTHROUGH"
]
