import os
import sys

from .compat import is_win32, is_py2

DEFAULT_PLAYER_ARGUMENTS = "{filename}"

if is_win32:
    APPDATA = os.environ["APPDATA"]
    CONFIG_FILE = os.path.join(APPDATA, "livestreamer", "livestreamerrc")
    PLUGINS_DIR = os.path.join(APPDATA, "livestreamer", "plugins")
else:
    XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    CONFIG_FILE = os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/config")
    PLUGINS_DIR = os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/plugins")

    if not os.path.isfile(CONFIG_FILE):
        CONFIG_FILE = os.path.expanduser("~/.livestreamerrc")

if is_py2:
    PLUGINS_DIR = PLUGINS_DIR.decode(sys.getfilesystemencoding())
    CONFIG_FILE = CONFIG_FILE.decode(sys.getfilesystemencoding())


EXAMPLE_USAGE = """
example usage:

$ livestreamer twitch.tv/thegdstudio
Available streams: high, low, medium, mobile (worst), source (best)
$ livestreamer twitch.tv/thegdstudio high

Stream is now opened in player (default is VLC, if installed).

"""

STREAM_SYNONYMS = ["best", "worst"]
STREAM_PASSTHROUGH = ["hls", "http", "rtmp"]

__all__ = ["EXAMPLE_USAGE", "CONFIG_FILE", "PLUGINS_DIR",
           "STREAM_SYNONYMS", "STREAM_PASSTHROUGH", "DEFAULT_PLAYER_ARGUMENTS"]
