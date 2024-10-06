from __future__ import annotations

import re
from typing import Any, Generic, TypeVar


_BOOLEAN_TRUE = "yes", "1", "true", "on"
_BOOLEAN_FALSE = "no", "0", "false", "off"

_FILESIZE_RE = re.compile(r"^(?P<size>\d+(\.\d+)?)(?P<modifier>[km])?b?$", re.IGNORECASE)
_FILESIZE_UNITS = {
    "k": 2**10,
    "m": 2**20,
}

_KEYVALUE_RE = re.compile(r"^(?P<key>[^=\s]+)\s*=\s*(?P<value>.*)$")


def boolean(value: str) -> bool:
    if value.lower() not in _BOOLEAN_TRUE + _BOOLEAN_FALSE:
        raise ValueError(f"{value} is not one of {{{', '.join(_BOOLEAN_TRUE + _BOOLEAN_FALSE)}}}")

    return value.lower() in _BOOLEAN_TRUE


def comma_list(values: str) -> list[str]:
    return [val.strip() for val in values.split(",")]


# noinspection PyPep8Naming
class comma_list_filter:
    def __init__(self, acceptable: list[str], unique: bool = False):
        self.acceptable = tuple(acceptable)
        self.unique = unique

    def __call__(self, values: str) -> list[str]:
        res = [item for item in comma_list(values) if item in self.acceptable]
        return sorted(set(res)) if self.unique else res

    def __hash__(self):
        return hash((self.acceptable, self.unique))


def filesize(value: str) -> int:
    match = _FILESIZE_RE.match(value.strip())
    if not match:
        raise ValueError("Invalid file size format")

    size = float(match["size"])
    size *= _FILESIZE_UNITS.get((match["modifier"] or "").lower(), 1)

    return num(int, ge=1)(size)


def keyvalue(value: str) -> tuple[str, str]:
    match = _KEYVALUE_RE.match(value.lstrip())
    if not match:
        raise ValueError("Invalid key=value format")

    return match["key"], match["value"]


_TNum = TypeVar("_TNum", int, float)


# noinspection PyPep8Naming
class num(Generic[_TNum]):
    def __init__(
        self,
        numtype: type[_TNum],
        ge: _TNum | None = None,
        gt: _TNum | None = None,
        le: _TNum | None = None,
        lt: _TNum | None = None,
    ):
        self.numtype: type[_TNum] = numtype
        self.ge: _TNum | None = ge
        self.gt: _TNum | None = gt
        self.le: _TNum | None = le
        self.lt: _TNum | None = lt
        self.__name__ = numtype.__name__

    def __call__(self, value: Any) -> _TNum:
        val: _TNum = self.numtype(value)

        if self.ge is not None and val < self.ge:
            raise ValueError(f"{self.__name__} value must be >={self.ge}, but is {val}")
        if self.gt is not None and val <= self.gt:
            raise ValueError(f"{self.__name__} value must be >{self.gt}, but is {val}")
        if self.le is not None and val > self.le:
            raise ValueError(f"{self.__name__} value must be <={self.le}, but is {val}")
        if self.lt is not None and val >= self.lt:
            raise ValueError(f"{self.__name__} value must be <{self.lt}, but is {val}")

        return val

    def __hash__(self) -> int:
        return hash((self.numtype, self.ge, self.gt, self.le, self.lt))


__all__ = [
    "boolean",
    "comma_list",
    "comma_list_filter",
    "filesize",
    "keyvalue",
    "num",
]
