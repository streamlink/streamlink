import re
from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar


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


def comma_list(values: str) -> List[str]:
    return [val.strip() for val in values.split(",")]


# noinspection PyPep8Naming
class comma_list_filter:
    def __init__(self, acceptable: List[str], unique: bool = False):
        self.acceptable = tuple(acceptable)
        self.unique = unique

    def __call__(self, values: str) -> List[str]:
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


def keyvalue(value: str) -> Tuple[str, str]:
    match = _KEYVALUE_RE.match(value.lstrip())
    if not match:
        raise ValueError("Invalid key=value format")

    return match["key"], match["value"]


_TNum = TypeVar("_TNum", int, float)


# noinspection PyPep8Naming
class num(Generic[_TNum]):
    def __init__(
        self,
        numtype: Type[_TNum],
        ge: Optional[_TNum] = None,
        gt: Optional[_TNum] = None,
        le: Optional[_TNum] = None,
        lt: Optional[_TNum] = None,
    ):
        self.numtype: Type[_TNum] = numtype
        self.ge: Optional[_TNum] = ge
        self.gt: Optional[_TNum] = gt
        self.le: Optional[_TNum] = le
        self.lt: Optional[_TNum] = lt
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
