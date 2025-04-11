from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from math import floor
from pathlib import PurePath
from string import Formatter as StringFormatter
from threading import Event, RLock, Thread
from time import time
from typing import TYPE_CHECKING

from streamlink_cli.console.console import ConsoleOutput
from streamlink_cli.console.terminal import cut_text, term_width, text_width


if TYPE_CHECKING:
    from typing_extensions import TypeAlias


_stringformatter = StringFormatter()
_TFormat: TypeAlias = "Iterable[Iterable[tuple[str, str | None, str | None, str | None]]]"


class ProgressFormatter:
    # Store formats as a tuple of lists of parsed format strings,
    # so when iterating, we don't have to parse over and over again.
    # Reserve at least 15 characters for the path, so it can be truncated with enough useful information.
    FORMATS: _TFormat = tuple(
        list(_stringformatter.parse(fmt))
        for fmt in (
            "[download] Written {written} to {path:15} ({elapsed} @ {speed})",
            "[download] Written {written} ({elapsed} @ {speed})",
            "[download] {written} ({elapsed} @ {speed})",
            "[download] {written} ({elapsed})",
            "[download] {written}",
        )
    )
    FORMATS_NOSPEED: _TFormat = tuple(
        list(_stringformatter.parse(fmt))
        for fmt in (
            "[download] Written {written} to {path:15} ({elapsed})",
            "[download] Written {written} ({elapsed})",
            "[download] {written} ({elapsed})",
            "[download] {written}",
        )
    )

    # Use U+2026 (HORIZONTAL ELLIPSIS) to be able to distinguish between "." and ".." when truncating relative paths
    ELLIPSIS: str = "…"

    @classmethod
    def format(cls, formats: _TFormat, params: Mapping[str, str | Callable[[int], str]]) -> str:
        width = term_width()
        static: list[str] = []
        variable: list[tuple[int, Callable[[int], str], int]] = []

        for fmt in formats:
            static.clear()
            variable.clear()
            length = 0
            # Get literal texts, static segments and variable segments from the parsed format
            # and calculate the overall length of the literal texts and static segments after substituting them.
            for literal_text, field_name, format_spec, _conversion in fmt:
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
                    if length > width:
                        continue
                    else:
                        break

                # Get the available space for each variable segment (share space equally and round down).
                max_width = int((width - length) / len(variable))
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
        return floor(num * 10**n) / 10**n

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
        width = text_width(string)
        if width <= max_width:
            return string

        # Since the path doesn't fit, we always need to add an ellipsis.
        # On Windows, we also need to add the "drive" part (which is an empty string on PurePosixPath)
        max_width -= text_width(path.drive) + text_width(cls.ELLIPSIS)

        # Ignore the path's first part, aka the "anchor" (drive + root)
        parts = os.path.sep.join(path.parts[1:] if path.drive else path.parts)
        truncated = cut_text(parts, max_width)

        return f"{path.drive}{cls.ELLIPSIS}{truncated}"


class Progress(Thread):
    def __init__(
        self,
        console: ConsoleOutput,
        path: PurePath,
        interval: float = 0.25,
        history: int = 20,
        threshold: int = 2,
        status: bool = True,
    ):
        """
        :param console: The console output
        :param interval: Time in seconds between updates
        :param history: Number of seconds of how long download speed history is kept
        :param threshold: Number of seconds until download speed is shown
        """

        super().__init__(daemon=True)
        self._wait = Event()
        self._lock = RLock()

        self.formatter = ProgressFormatter()

        self.console: ConsoleOutput = console
        self.path: PurePath = path
        self.interval: float = interval
        self.history: deque[tuple[float, int]] = deque(maxlen=int(history / interval))
        self.threshold: int = int(threshold / interval)

        self.started: float = 0.0
        self.overall: int = 0
        self.written: int = 0
        self.status: bool = status

    def close(self):
        self._wait.set()

    def write(self, chunk: bytes):
        size = len(chunk)
        with self._lock:
            self.overall += size
            self.written += size

    def run(self):
        self.started = time()
        try:
            while not self._wait.wait(self.interval):
                self.update()
        finally:
            self.update()

    def update(self):
        with self._lock:
            now = time()
            formatter = self.formatter
            history = self.history

            history.append((now, self.written))
            self.written = 0

            has_history = len(history) >= self.threshold
            if not has_history or now == history[0][0]:
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
            if self.status:
                self.console.msg_status(status)
            else:
                self.console.msg(status)
