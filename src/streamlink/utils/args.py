import re
from typing import Any, Callable, List, Optional, Tuple, Type, overload


_BOOLEAN_TRUE = "yes", "1", "true", "on"
_BOOLEAN_FALSE = "no", "0", "false", "off"

_FILESIZE_RE = re.compile(r"(?P<size>\d+(\.\d+)?)(?P<modifier>[km])?b?", re.IGNORECASE)
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


def comma_list_filter(acceptable: List[str]) -> Callable[[str], List[str]]:
    def func(values: str) -> List[str]:
        return [item for item in comma_list(values) if item in acceptable]

    return func


def filesize(value: str) -> int:
    match = _FILESIZE_RE.match(value)
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


@overload
def num(
    numtype: Type[int],
    ge: Optional[int] = None,
    gt: Optional[int] = None,
    le: Optional[int] = None,
    lt: Optional[int] = None,
) -> Callable[[Any], int]: pass  # pragma: no cover


@overload
def num(
    numtype: Type[float],
    ge: Optional[float] = None,
    gt: Optional[float] = None,
    le: Optional[float] = None,
    lt: Optional[float] = None,
) -> Callable[[Any], float]: pass  # pragma: no cover


def num(
    numtype: Type[float],
    ge: Optional[float] = None,
    gt: Optional[float] = None,
    le: Optional[float] = None,
    lt: Optional[float] = None,
) -> Callable[[Any], float]:
    def func(value: Any) -> float:
        value = numtype(value)

        if ge is not None and value < ge:
            raise ValueError(f"{numtype.__name__} value must be >={ge}, but is {value}")
        if gt is not None and value <= gt:
            raise ValueError(f"{numtype.__name__} value must be >{gt}, but is {value}")
        if le is not None and value > le:
            raise ValueError(f"{numtype.__name__} value must be <={le}, but is {value}")
        if lt is not None and value >= lt:
            raise ValueError(f"{numtype.__name__} value must be <{lt}, but is {value}")

        return value

    func.__name__ = numtype.__name__

    return func


__all__ = [
    "boolean",
    "comma_list",
    "comma_list_filter",
    "filesize",
    "keyvalue",
    "num",
]
