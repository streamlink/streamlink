from shutil import get_terminal_size
from typing import Iterable

from streamlink.compat import is_win32


# widths generated from
# https://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt
# See https://github.com/streamlink/streamlink/pull/2032
WIDTHS: Iterable[tuple[int, int]] = (
    (13, 1),
    (15, 0),
    (126, 1),
    (159, 0),
    (687, 1),
    (710, 0),
    (711, 1),
    (727, 0),
    (733, 1),
    (879, 0),
    (1154, 1),
    (1161, 0),
    (4347, 1),
    (4447, 2),
    (7467, 1),
    (7521, 0),
    (8369, 1),
    (8426, 0),
    (9000, 1),
    (9002, 2),
    (11021, 1),
    (12350, 2),
    (12351, 1),
    (12438, 2),
    (12442, 0),
    (19893, 2),
    (19967, 1),
    (55203, 2),
    (63743, 1),
    (64106, 2),
    (65039, 1),
    (65059, 0),
    (65131, 2),
    (65279, 1),
    (65376, 2),
    (65500, 1),
    (65510, 2),
    (120831, 1),
    (262141, 2),
    (1114109, 1),
)

# On Windows, we need one less space, or we overflow the line for some reason.
GAP = 1 if is_win32 else 0


def term_width():
    return get_terminal_size().columns - GAP


def _get_width(ordinal: int) -> int:
    """Return the width of a specific unicode character when it would be displayed."""
    return next((width for unicode, width in WIDTHS if ordinal <= unicode), 1)


def text_width(value: str):
    """Return the overall width of a string when it would be displayed."""
    return sum(map(_get_width, map(ord, value)))


def cut_text(value: str, max_width: int) -> str:
    """Cut off the beginning of a string until its display width fits into the output size."""
    current = value
    for i in range(len(value)):  # pragma: no branch
        current = value[i:]
        if text_width(current) <= max_width:
            break

    return current
