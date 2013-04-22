import os
import sys

from .compat import is_win32

DEFAULT_PLAYER = "vlc"

if "darwin" in sys.platform:
    DEFAULT_PLAYER = "/Applications/VLC.app/Contents/MacOS/VLC"
elif "win32" in sys.platform:
    exepath = "VideoLAN\\VLC\\vlc.exe"
    envvars = ["PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"]

    # Expand each environment variable to a path if it exists,
    # then check if VLC exists in that path.
    for var in envvars:
        if var in os.environ:
            path = os.path.join(os.environ[var], exepath)
            if os.path.exists(path):
                DEFAULT_PLAYER = '"{0}"'.format(path)
                break

if is_win32:
    CONFIG_FILE = os.path.join(os.environ["APPDATA"], "livestreamer", "livestreamerrc")
    PLUGINS_DIR = os.path.join(os.environ["APPDATA"], "livestreamer", "plugins")
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

Stream now playbacks in player (default is {0}).

""".format(DEFAULT_PLAYER)

STREAM_SYNONYMS = ["best", "worst"]

__all__ = ["DEFAULT_PLAYER", "EXAMPLE_USAGE", "CONFIG_FILE", "PLUGINS_DIR", "STREAM_SYNONYMS"]
