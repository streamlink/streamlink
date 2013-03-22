import os
import sys

is_py2 = (sys.version_info[0] == 2)
is_py3 = (sys.version_info[0] == 3)
is_win32 = os.name == "nt"
is_32bit = sys.maxsize == 0x7fffffff

if is_py2:
    input = raw_input
    stdout = sys.stdout
    file = file

elif is_py3:
    input = input
    stdout = sys.stdout.buffer
    from io import IOBase as file

__all__ = ["is_py2", "is_py3", "is_win32", "is_32bit", "input", "stdout", "file"]
