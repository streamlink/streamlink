import sys
from os import devnull
from typing import BinaryIO


try:
    stdout: BinaryIO = sys.stdout.buffer
except AttributeError:  # pragma: no cover
    from atexit import register as _atexit_register
    from pathlib import Path

    stdout = Path(devnull).open("wb")
    _atexit_register(stdout.close)
    del _atexit_register


__all__ = [
    "stdout",
]
