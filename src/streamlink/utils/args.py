import argparse
import re


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

    return num(int, min=0)(size)


def keyvalue(value):
    match = _keyvalue_re.match(value)
    if not match:
        raise ValueError

    return match.group("key", "value")


# noinspection PyShadowingBuiltins
def num(type, min=None, max=None):  # noqa: A002
    def func(value):
        value = type(value)

        if min is not None and not (value > min):
            raise argparse.ArgumentTypeError(
                "{0} value must be more than {1} but is {2}".format(
                    type.__name__, min, value,
                ),
            )

        if max is not None and not (value <= max):
            raise argparse.ArgumentTypeError(
                "{0} value must be at most {1} but is {2}".format(
                    type.__name__, max, value,
                ),
            )

        return value

    func.__name__ = type.__name__

    return func


__all__ = [
    "boolean", "comma_list", "comma_list_filter", "filesize", "keyvalue",
    "num",
]
