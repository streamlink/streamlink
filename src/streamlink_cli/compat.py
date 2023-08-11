import sys
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO


stdout: BinaryIO = sys.stdout.buffer


if TYPE_CHECKING:  # pragma: no cover
    _BasePath = Path
else:
    _BasePath = type(Path())


class DeprecatedPath(_BasePath):
    pass


__all__ = [
    "stdout",
    "DeprecatedPath",
]
