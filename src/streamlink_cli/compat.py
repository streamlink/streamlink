import os
import sys

is_win32 = os.name == "nt"

input = input
stdout = sys.stdout.buffer
from io import IOBase as file
from shutil import get_terminal_size


__all__ = ["is_win32", "input", "stdout", "file",
           "get_terminal_size"]
