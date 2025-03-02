import sys
from atexit import register as _atexit_register
from os import devnull as _devnull
from typing import BinaryIO


devnull_bin = open(_devnull, "wb")
_atexit_register(devnull_bin.close)
devnull_txt = open(_devnull, "w", encoding=None)
_atexit_register(devnull_txt.close)

try:
    stdout_or_devnull_bin: BinaryIO = sys.stdout.buffer
except AttributeError:  # pragma: no cover
    stdout_or_devnull_bin = devnull_bin

del _atexit_register, _devnull


__all__ = [
    "devnull_bin",
    "devnull_txt",
    "stdout_or_devnull_bin",
]
