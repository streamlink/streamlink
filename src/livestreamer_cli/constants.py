import os
import sys

from .compat import is_win32


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
else:
    DEFAULT_PLAYER = "vlc"


if is_win32:
    RCFILE = os.path.join(os.environ["APPDATA"], "livestreamer", "livestreamerrc")
else:
    RCFILE = os.path.expanduser("~/.livestreamerrc")


EXAMPLE_USAGE = """
example usage:

$ livestreamer twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, iphonehigh, iphonelow (worst), live (best)
$ livestreamer twitch.tv/onemoregametv 720p

Stream now playbacks in player (default is {0}).

""".format(DEFAULT_PLAYER)

STREAM_SYNONYMS = ["best", "worst"]

__all__ = ["DEFAULT_PLAYER", "EXAMPLE_USAGE", "RCFILE", "STREAM_SYNONYMS"]
