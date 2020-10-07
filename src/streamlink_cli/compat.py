import os
import sys

is_win32 = os.name == "nt"

stdout = sys.stdout.buffer
from io import IOBase as file
from shutil import get_terminal_size


__all__ = ["is_win32", "stdout", "file",
           "get_terminal_size"]
