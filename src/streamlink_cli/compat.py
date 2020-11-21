import os
import sys

is_win32 = os.name == "nt"

stdout = sys.stdout.buffer


__all__ = ["is_win32", "stdout"]
