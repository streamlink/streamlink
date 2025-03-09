from __future__ import annotations

import sys
from atexit import register as _atexit_register
from os import devnull as _devnull
from typing import Any, BinaryIO, Callable, TextIO


_LAZY_ATTRS: dict[str, Callable[[], Any]] = {}


def __getattr__(key: str):
    if fn := _LAZY_ATTRS.get(key):
        res = fn()
        globals()[key] = res
        del _LAZY_ATTRS[key]
        return res

    raise AttributeError(f"Module {__name__!r} has no attribute {key!r}")


def _lazy_fd(name: str, path: str, mode: str, **params):
    def lazy_open():
        fd = open(path, mode, **params)
        _atexit_register(fd.close)

        return fd

    _LAZY_ATTRS[name] = lazy_open


devnull_bin: BinaryIO
devnull_txt: TextIO
_lazy_fd("devnull_bin", _devnull, "wb")
_lazy_fd("devnull_txt", _devnull, "w", encoding=None)


try:
    stdout_or_devnull_bin: BinaryIO = sys.stdout.buffer
except AttributeError:
    stdout_or_devnull_bin = __getattr__("devnull_bin")


__all__ = [
    "devnull_bin",
    "devnull_txt",
    "stdout_or_devnull_bin",
]
