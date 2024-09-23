import sys
from os import devnull
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO


try:
    stdout: BinaryIO = sys.stdout.buffer
except AttributeError:  # pragma: no cover
    from atexit import register as _atexit_register

    stdout = open(devnull, "wb")
    _atexit_register(stdout.close)
    del _atexit_register


if TYPE_CHECKING:  # pragma: no cover
    _BasePath = Path
else:
    _BasePath = type(Path())


class DeprecatedPath(_BasePath):
    pass


__all__ = [
    "DeprecatedPath",
    "stdout",
]
