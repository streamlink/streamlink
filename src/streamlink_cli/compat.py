import os
import sys
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

try:
    import importlib.metadata as importlib_metadata  # type: ignore[import]  # noqa: F401
except ImportError:
    import importlib_metadata  # type: ignore[import]  # noqa: F401


is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"

stdout: BinaryIO = sys.stdout.buffer


if TYPE_CHECKING:  # pragma: no cover
    _BasePath = Path
else:
    _BasePath = type(Path())


class DeprecatedPath(_BasePath):
    pass


__all__ = ["is_darwin", "is_win32", "stdout", "DeprecatedPath"]
