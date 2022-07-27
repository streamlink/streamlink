import os
import sys


is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"

# win/nix compatible devnull
try:
    from subprocess import DEVNULL

    def devnull():
        return DEVNULL
except ImportError:
    def devnull():
        return open(os.path.devnull, 'w')


__all__ = [
    "is_darwin",
    "is_win32",
    "devnull",
]
