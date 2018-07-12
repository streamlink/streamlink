import re

_hours_minutes_seconds_re = re.compile(r"""
    ^-?(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)$
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


__all__ = [
    "hours_minutes_seconds",
]
