import os
import sys

is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"

stdout = sys.stdout.buffer


__all__ = ["is_darwin", "is_win32", "stdout"]
