from shutil import get_terminal_size
from sys import stderr
from typing import TextIO

from streamlink.compat import is_win32


class TerminalOutput:
    # widths generated from
    # https://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt
    # See https://github.com/streamlink/streamlink/pull/2032
    WIDTHS = (
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

    def __init__(self, stream: TextIO = stderr):
        self.stream = stream

    @classmethod
    def _get_width(cls, ordinal: int) -> int:
        """Returns the width of a specific unicode character when it would be displayed."""
        for unicode, width in cls.WIDTHS:  # pragma: no branch
            if ordinal <= unicode:
                return width
        return 1  # pragma: no cover

    @classmethod
    def term_width(cls):
        return get_terminal_size().columns

    @classmethod
    def width(cls, value: str):
        """Returns the overall width of a string when it would be displayed."""
        return sum(map(cls._get_width, map(ord, value)))

    @classmethod
    def cut(cls, value: str, max_len: int) -> str:
        """Cuts off the beginning of a string until its display width fits into the output size."""
        current = value
        for i in range(len(value)):  # pragma: no branch
            current = value[i:]
            if cls.width(current) <= max_len:
                break
        return current

    def print_inplace(self, msg: str):
        """Clears the previous line and prints a new one."""
        term_width = self.term_width()
        spacing = term_width - self.width(msg)

        # On Windows, we need one less space, or we overflow the line for some reason.
        if is_win32:
            spacing -= 1

        self.stream.write(f"\r{msg}")
        self.stream.write(" " * max(0, spacing))
        self.stream.flush()

    def end(self):
        self.stream.write("\n")
        self.stream.flush()
