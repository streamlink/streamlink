import re
from datetime import datetime, timezone, tzinfo

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


_hours_minutes_seconds_re = re.compile(r"""
    ^-?(?:(?P<hours>\d+):)?(?P<minutes>\d+):(?P<seconds>\d+)$
""", re.VERBOSE)

_hours_minutes_seconds_2_re = re.compile(r"""^-?
    (?:
        (?P<hours>\d+)h
    )?
    (?:
        (?P<minutes>\d+)m
    )?
    (?:
        (?P<seconds>\d+)s
    )?$
""", re.VERBOSE | re.IGNORECASE)


def hours_minutes_seconds(value):
    """converts a timestamp to seconds

      - hours:minutes:seconds to seconds
      - minutes:seconds to seconds
      - 11h22m33s to seconds
      - 11h to seconds
      - 20h15m to seconds
      - seconds to seconds

    :param value: hh:mm:ss ; 00h00m00s ; seconds
    :return: seconds
    """
    try:
        return int(value)
    except ValueError:
        pass

    match = (_hours_minutes_seconds_re.match(value)
             or _hours_minutes_seconds_2_re.match(value))
    if not match:
        raise ValueError

    s = 0
    s += int(match.group("hours") or "0") * 60 * 60
    s += int(match.group("minutes") or "0") * 60
    s += int(match.group("seconds") or "0")

    return s


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
    "seconds_to_hhmmss",
]
