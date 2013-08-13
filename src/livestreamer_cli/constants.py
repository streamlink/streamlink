import os

from .compat import is_win32

if is_win32:
    CONFIG_FILE = os.path.join(os.environ["APPDATA"], "livestreamer",
                               "livestreamerrc")
    PLUGINS_DIR = os.path.join(os.environ["APPDATA"], "livestreamer",
                               "plugins")
else:
    XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME",
                                     "~/.config")

    CONFIG_FILE = os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/config")
    PLUGINS_DIR = os.path.expanduser(XDG_CONFIG_HOME + "/livestreamer/plugins")

    if not os.path.isfile(CONFIG_FILE):
        CONFIG_FILE = os.path.expanduser("~/.livestreamerrc")


EXAMPLE_USAGE = """
example usage:

$ livestreamer twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, mobile_high, mobile_low (worst), 1080p+ (best)
$ livestreamer twitch.tv/onemoregametv 720p

Stream is now opened in player (default is VLC, if installed).

"""

STREAM_SYNONYMS = ["best", "worst"]

__all__ = ["EXAMPLE_USAGE", "CONFIG_FILE", "PLUGINS_DIR", "STREAM_SYNONYMS"]
