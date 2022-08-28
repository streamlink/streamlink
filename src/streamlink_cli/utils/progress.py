import os
from collections import deque
from math import floor
from pathlib import PurePath
from shutil import get_terminal_size
from string import Formatter as StringFormatter
from threading import Event, RLock, Thread
from time import time
from typing import Callable, Deque, Dict, Iterable, Iterator, List, Optional, TextIO, Tuple, Union

from streamlink.compat import is_win32


_stringformatter = StringFormatter()
_TFormat = Iterable[Iterable[Tuple[str, Optional[str], Optional[str], Optional[str]]]]


class ProgressFormatter:
    # Store formats as a tuple of lists of parsed format strings,
    # so when iterating, we don't have to parse over and over again.
    # Reserve at least 15 characters for the path, so it can be truncated with enough useful information.
    FORMATS: _TFormat = tuple(list(_stringformatter.parse(fmt)) for fmt in (
        "[download] Written {written} to {path:15} ({elapsed} @ {speed})",
        "[download] Written {written} ({elapsed} @ {speed})",
        "[download] {written} ({elapsed} @ {speed})",
        "[download] {written} ({elapsed})",
        "[download] {written}",
    ))
    FORMATS_NOSPEED: _TFormat = tuple(list(_stringformatter.parse(fmt)) for fmt in (
        "[download] Written {written} to {path:15} ({elapsed})",
        "[download] Written {written} ({elapsed})",
        "[download] {written} ({elapsed})",
        "[download] {written}",
    ))

    # Use U+2026 (HORIZONTAL ELLIPSIS) to be able to distinguish between "." and ".." when truncating relative paths
    ELLIPSIS: str = "…"

    # widths generated from
    # https://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt
    # See https://github.com/streamlink/streamlink/pull/2032
    WIDTHS: Iterable[Tuple[int, int]] = (
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
    gap = 1 if is_win32 else 0

    @classmethod
    def term_width(cls):
        return get_terminal_size().columns - cls.gap

    @classmethod
    def _get_width(cls, ordinal: int) -> int:
        """Return the width of a specific unicode character when it would be displayed."""
        return next((width for unicode, width in cls.WIDTHS if ordinal <= unicode), 1)

    @classmethod
    def width(cls, value: str):
        """Return the overall width of a string when it would be displayed."""
        return sum(map(cls._get_width, map(ord, value)))

    @classmethod
    def cut(cls, value: str, max_width: int) -> str:
        """Cut off the beginning of a string until its display width fits into the output size."""
        current = value
        for i in range(len(value)):  # pragma: no branch
            current = value[i:]
            if cls.width(current) <= max_width:
                break
        return current

    @classmethod
    def format(cls, formats: _TFormat, params: Dict[str, Union[str, Callable[[int], str]]]) -> str:
        term_width = cls.term_width()
        static: List[str] = []
        variable: List[Tuple[int, Callable[[int], str], int]] = []

        for fmt in formats:
            static.clear()
            variable.clear()
            length = 0
            # Get literal texts, static segments and variable segments from the parsed format
            # and calculate the overall length of the literal texts and static segments after substituting them.
            for literal_text, field_name, format_spec, conversion in fmt:
                static.append(literal_text)
                length += len(literal_text)
                if field_name is None:
                    continue
                if field_name not in params:
                    break
                value_or_callable = params[field_name]
                if not callable(value_or_callable):
                    static.append(value_or_callable)
                    length += len(value_or_callable)
                else:
                    variable.append((len(static), value_or_callable, int(format_spec or 0)))
                    static.append("")
            else:
                # No variable segments? Just check if the resulting string fits into the size constraints.
                if not variable:
                    if length > term_width:
                        continue
                    else:
                        break

                # Get the available space for each variable segment (share space equally and round down).
                max_width = int((term_width - length) / len(variable))
                # If at least one variable segment doesn't fit, continue with the next format.
                if max_width < 1 or any(max_width < min_width for _, __, min_width in variable):
                    continue
                # All variable segments fit, so finally format them, but continue with the next format if there's an error.
                # noinspection PyBroadException
                try:
                    for idx, fn, _ in variable:
                        static[idx] = fn(max_width)
                except Exception:
                    continue
                break

        return "".join(static)

    @staticmethod
    def _round(num: float, n: int = 2) -> float:
        return floor(num * 10 ** n) / 10 ** n

    @classmethod
    def format_filesize(cls, size: float, suffix: str = "") -> str:
        if size < 1024:
            return f"{size:.0f} bytes{suffix}"
        if size < 2**20:
            return f"{cls._round(size / 2**10, 2):.2f} KiB{suffix}"
        if size < 2**30:
            return f"{cls._round(size / 2**20, 2):.2f} MiB{suffix}"
        if size < 2**40:
            return f"{cls._round(size / 2**30, 2):.2f} GiB{suffix}"

        return f"{cls._round(size / 2**40, 2):.2f} TiB{suffix}"

    @classmethod
    def format_time(cls, elapsed: float) -> str:
        elapsed = max(elapsed, 0)

        if elapsed < 60:
            return f"{int(elapsed % 60):1d}s"
        if elapsed < 3600:
            return f"{int(elapsed % 3600 / 60):1d}m{int(elapsed % 60):02d}s"

        return f"{int(elapsed / 3600)}h{int(elapsed % 3600 / 60):02d}m{int(elapsed % 60):02d}s"

    @classmethod
    def format_path(cls, path: PurePath, max_width: int) -> str:
        # Quick check if the path fits
        string = str(path)
        width = cls.width(string)
        if width <= max_width:
            return string

        # Since the path doesn't fit, we always need to add an ellipsis.
        # On Windows, we also need to add the "drive" part (which is an empty string on PurePosixPath)
        max_width -= cls.width(path.drive) + cls.width(cls.ELLIPSIS)

        # Ignore the path's first part, aka the "anchor" (drive + root)
        parts = os.path.sep.join(path.parts[1:])
        truncated = cls.cut(parts, max_width)

        return f"{path.drive}{cls.ELLIPSIS}{truncated}"


class Progress(Thread):
    def __init__(
        self,
        stream: TextIO,
        path: PurePath,
        interval: float = 0.25,
        history: int = 20,
        threshold: int = 2,
    ):
        """
        :param stream: The output stream
        :param path: The path that's being written
        :param interval: Time in seconds between updates
        :param history: Number of seconds of how long download speed history is kept
        :param threshold: Number of seconds until download speed is shown
        """

        super().__init__(daemon=True)
        self._wait = Event()
        self._lock = RLock()

        self.formatter = ProgressFormatter()

        self.stream: TextIO = stream
        self.path: PurePath = path
        self.interval: float = interval
        self.history: Deque[Tuple[float, int]] = deque(maxlen=int(history / interval))
        self.threshold: int = int(threshold / interval)

        self.started: float = 0.0
        self.overall: int = 0
        self.written: int = 0

    def close(self):
        self._wait.set()

    def put(self, chunk: bytes):
        size = len(chunk)
        with self._lock:
            self.overall += size
            self.written += size

    def iter(self, iterator: Iterator[bytes]) -> Iterator[bytes]:
        self.start()
        try:
            for chunk in iterator:
                self.put(chunk)
                yield chunk
        finally:
            self.close()

    def run(self):
        self.started = time()
        try:
            while not self._wait.wait(self.interval):
                self.update()
        finally:
            self.print_end()

    def update(self):
        with self._lock:
            now = time()
            formatter = self.formatter
            history = self.history

            history.append((now, self.written))
            self.written = 0

            has_history = len(history) >= self.threshold
            if not has_history:
                formats = formatter.FORMATS_NOSPEED
                speed = ""
            else:
                formats = formatter.FORMATS
                speed = formatter.format_filesize(sum(size for _, size in history) / (now - history[0][0]), "/s")

            params = dict(
                written=formatter.format_filesize(self.overall),
                elapsed=formatter.format_time(now - self.started),
                speed=speed,
                path=lambda max_width: formatter.format_path(self.path, max_width),
            )

            status = formatter.format(formats, params)

            self.print_inplace(status)

    def print_inplace(self, msg: str):
        """Clears the previous line and prints a new one."""
        term_width = self.formatter.term_width()
        spacing = term_width - self.formatter.width(msg)

        self.stream.write(f"\r{msg}{' ' * max(0, spacing)}")
        self.stream.flush()

    def print_end(self):
        self.stream.write("\n")
        self.stream.flush()
