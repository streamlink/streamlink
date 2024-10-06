from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone, tzinfo
from typing import Generic, TypeVar

from isodate import LOCAL, parse_datetime  # type: ignore[import]


UTC = timezone.utc


def now(tz: tzinfo = UTC) -> datetime:
    return datetime.now(tz=tz)


def localnow() -> datetime:
    return datetime.now(tz=LOCAL)


def fromtimestamp(timestamp: float, tz: tzinfo = UTC) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=tz)


def fromlocaltimestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=LOCAL)


_THMS = TypeVar("_THMS", int, float)


class _HoursMinutesSeconds(Generic[_THMS]):
    """
    Convert an optionally negative HMS-timestamp string to seconds, as float or int

    Accepted formats:

    - seconds
    - minutes":"seconds
    - hours":"minutes":"seconds
    - seconds"s"
    - minutes"m"
    - hours"h"
    - minutes"m"seconds"s"
    - hours"h"seconds"s"
    - hours"h"minutes"m"
    - hours"h"minutes"m"seconds"s"
    """

    __name__ = "hours_minutes_seconds"

    _re_float = re.compile(
        r"^-?\d+(?:\.\d+)?$",
    )
    _re_s = re.compile(
        r"""
            ^
            -?
            (?P<seconds>\d+(?:\.\d+)?)
            s
            $
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    # noinspection RegExpSuspiciousBackref
    _re_ms = re.compile(
        r"""
            ^
            -?
            (?P<minutes>\d+)
            (?:(?P<sep>m)|:(?=.))
            (?:
                (?P<seconds>[0-5]?[0-9](?:\.\d+)?)
                (?(sep)s|)
            )?
            $
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    # noinspection RegExpSuspiciousBackref
    _re_hms = re.compile(
        r"""
            ^
            -?
            (?P<hours>\d+)
            (?:(?P<sep>h)|:(?=.))
            (?:
                (?P<minutes>[0-5]?[0-9])
                (?(sep)m|:(?=.))
            )?
            (?:
                (?P<seconds>[0-5]?[0-9](?:\.\d+)?)
                (?(sep)s|)
            )?
            $
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __init__(self, return_type: type[_THMS]):
        self._return_type: type[_THMS] = return_type

    def __call__(self, value: str) -> _THMS:
        if self._re_float.match(value):
            return self._return_type(float(value))

        match = self._re_s.match(value) or self._re_ms.match(value) or self._re_hms.match(value)
        if not match:
            raise ValueError

        data = match.groupdict()

        seconds = 0.0
        seconds += float(data.get("hours") or 0.0) * 3600.0
        seconds += float(data.get("minutes") or 0.0) * 60.0
        seconds += float(data.get("seconds") or 0.0)

        res = -seconds if value[0] == "-" else seconds

        return self._return_type(res)


hours_minutes_seconds: Callable[[str], int] = _HoursMinutesSeconds[int](int)
hours_minutes_seconds_float: Callable[[str], float] = _HoursMinutesSeconds[float](float)


def seconds_to_hhmmss(seconds):
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return "{0:02d}:{1:02d}:{2}".format(
        int(hours),
        int(minutes),
        "{0:02.1f}".format(seconds) if seconds % 1 else "{0:02d}".format(int(seconds)),
    )


__all__ = [
    "UTC",
    "LOCAL",
    "parse_datetime",
    "now",
    "localnow",
    "fromtimestamp",
    "fromlocaltimestamp",
    "hours_minutes_seconds",
    "hours_minutes_seconds_float",
    "seconds_to_hhmmss",
]
