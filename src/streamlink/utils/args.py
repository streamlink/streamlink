import argparse
import re
from typing import Optional, Type


_filesize_re = re.compile(r"""
    (?P<size>\d+(\.\d+)?)
    (?P<modifier>[Kk]|[Mm])?
    (?:[Bb])?
""", re.VERBOSE)
_keyvalue_re = re.compile(r"(?P<key>[^=]+)\s*=\s*(?P<value>.*)")


def boolean(value):
    truths = ["yes", "1", "true", "on"]
    falses = ["no", "0", "false", "off"]
    if value.lower() not in truths + falses:
        raise argparse.ArgumentTypeError("{0} was not one of {{{1}}}".format(
            value, ", ".join(truths + falses)))

    return value.lower() in truths


def comma_list(values):
    return [val.strip() for val in values.split(",")]


def comma_list_filter(acceptable):
    def func(p):
        values = comma_list(p)
        return list(filter(lambda v: v in acceptable, values))

    return func


def filesize(value):
    match = _filesize_re.match(value)
    if not match:
        raise ValueError

    size = float(match.group("size"))
    if not size:
        raise ValueError

    modifier = match.group("modifier")
    if modifier in ("M", "m"):
        size *= 1024 * 1024
    elif modifier in ("K", "k"):
        size *= 1024

    return num(int, ge=1)(size)


def keyvalue(value):
    match = _keyvalue_re.match(value)
    if not match:
        raise ValueError

    return match.group("key", "value")


def num(
    numtype: Type[float],
    ge: Optional[float] = None,
    gt: Optional[float] = None,
    le: Optional[float] = None,
    lt: Optional[float] = None,
):
    def func(value):
        value = numtype(value)

        if ge is not None and value < ge:
            raise argparse.ArgumentTypeError(f"{numtype.__name__} value must be >={ge}, but is {value}")
        if gt is not None and value <= gt:
            raise argparse.ArgumentTypeError(f"{numtype.__name__} value must be >{gt}, but is {value}")
        if le is not None and value > le:
            raise argparse.ArgumentTypeError(f"{numtype.__name__} value must be <={le}, but is {value}")
        if lt is not None and value >= lt:
            raise argparse.ArgumentTypeError(f"{numtype.__name__} value must be <{lt}, but is {value}")

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
