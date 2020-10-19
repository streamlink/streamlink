import os
import re
import sys
from io import IOBase as file
from shutil import get_terminal_size

is_win32 = os.name == "nt"

input = input
stdout = sys.stdout.buffer

_find_unsafe = re.compile(r"[^\w@%+=:,./-]", re.ASCII).search


__all__ = ["is_win32", "input", "stdout", "file", "get_terminal_size"]
