from collections import deque
from math import floor
from threading import Event, RLock, Thread
from time import time
from typing import Deque, Iterable, Iterator, Optional, Tuple

from streamlink_cli.utils.terminal import TerminalOutput


class ProgressFormatter:
    FORMATS: Iterable[str] = (
        "[download] Written {written} ({elapsed} @ {speed})",
        "[download] {written} ({elapsed} @ {speed})",
        "[download] {written} ({elapsed})",
        "[download] {written}",
    )
    FORMATS_NOSPEED: Iterable[str] = (
        "[download] Written {written} ({elapsed})",
        "[download] {written} ({elapsed})",
        "[download] {written}",
    )

    @classmethod
    def format(cls, max_size: int, formats: Iterable[str] = FORMATS, **params) -> str:
        output = ""

        for fmt in formats:
            output = fmt.format(**params)
            if len(output) <= max_size:
                break

        return output

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
        if elapsed < 0:
            elapsed = 0

        hours = ""
        minutes = ""

        if elapsed >= 3600:
            hours = f"{int(elapsed / (60 * 60))}h"
        if elapsed >= 60:
            if elapsed >= 3600:
                minutes = f"{int((elapsed % (60 * 60)) / 60):02d}m"
            else:
                minutes = f"{int((elapsed % (60 * 60)) / 60):1d}m"

        if elapsed >= 60:
            return f"{hours}{minutes}{int(elapsed % 60):02d}s"
        else:
            return f"{hours}{minutes}{int(elapsed % 60):1d}s"


class Progress(Thread):
    def __init__(
        self,
        output: Optional[TerminalOutput] = None,
        formatter: Optional[ProgressFormatter] = None,
        interval: float = 0.25,
        history: int = 20,
        threshold: int = 2,
    ):
        """
        :param output: The output class
        :param formatter: The formatter class
        :param interval: Time in seconds between updates
        :param history: Number of seconds of how long download speed history is kept
        :param threshold: Number of seconds until download speed is shown
        """

        super().__init__(daemon=True)
        self._wait = Event()
        self._lock = RLock()

        if output is None:
            output = TerminalOutput()
        if formatter is None:
            formatter = ProgressFormatter()

        self.output: TerminalOutput = output
        self.formatter: ProgressFormatter = formatter

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
            self.output.end()

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

            status = self.formatter.format(
                self.output.term_width() - 1,
                formats,
                written=formatter.format_filesize(self.overall),
                elapsed=formatter.format_time(now - self.started),
                speed=speed,
            )

            self.output.print_inplace(status)
