import os
import sys
from pathlib import Path


is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"

stdout = sys.stdout.buffer


class DeprecatedPath(type(Path())):
    pass


__all__ = ["is_darwin", "is_win32", "stdout", "DeprecatedPath"]
