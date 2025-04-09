from __future__ import annotations

import os
from io import TextIOWrapper
from threading import RLock
from typing import Iterable, Iterator

from streamlink.compat import is_win32
from streamlink_cli.console.stream_wrapper import StreamWrapper
from streamlink_cli.console.windows import WindowsConsole


class ConsoleStatusMessage(str):
    pass


class ConsoleOutputStream(StreamWrapper):
    def __new__(cls, stream: TextIOWrapper) -> ConsoleOutputStream:
        if stream.isatty():
            if (
                is_win32
                and (windows_console := WindowsConsole(stream))
                and not windows_console.supports_virtual_terminal_processing()
            ):
                console_output_stream_windows = super().__new__(ConsoleOutputStreamWindows)
                console_output_stream_windows.windows_console = windows_console
                return console_output_stream_windows

            if os.environ.get("TERM", "").lower() not in ("dumb", "unknown"):
                return super().__new__(ConsoleOutputStreamANSI)

        return super().__new__(cls)

    def __init__(self, stream: TextIOWrapper):
        super().__init__(stream)
        self._lock = RLock()
        self._line_buffer: list[str] = []

    @classmethod
    def supports_status_messages(cls):
        return False

    def _get_lines(self, msg: str) -> Iterator[str]:
        while msg:
            line, nl, msg = msg.partition("\n")
            if nl:
                yield f"{''.join(self._line_buffer)}{line}{nl}"
                self._line_buffer.clear()
            else:
                self._line_buffer.append(line)

    def close(self):
        with self._lock:
            if not self.closed:
                self.flush()

            return self._stream.close()

    def flush(self):
        with self._lock:
            if self._stream.closed:
                raise ValueError("I/O operation on closed file.")

            if rest := "".join(self._line_buffer):
                self._line_buffer.clear()
                self._stream.write(rest)
            self._stream.flush()

    def write(self, s: str) -> int:
        written = 0

        with self._lock:
            if self._stream.closed:
                raise ValueError("I/O operation on closed file.")

            if type(s) is not ConsoleStatusMessage:
                if lines := "".join(self._get_lines(s)):
                    written = self._stream.write(lines)

        return written

    def writelines(self, lines: Iterable[str], /) -> None:  # type: ignore[override]
        with self._lock:
            if self._stream.closed:
                raise ValueError("I/O operation on closed file.")

            self.write("".join(lines))


class _ConsoleOutputStreamWithStatusMessages(ConsoleOutputStream):
    def __init__(self, stream: TextIOWrapper):
        super().__init__(stream)
        self._last_status: str = ""

    @classmethod
    def supports_status_messages(cls):
        return True

    def clear_line(self, s: str) -> str:  # pragma: no cover
        return s

    def close(self):
        with self._lock:
            if not self.closed:
                if self._line_buffer:
                    if self._last_status:
                        s = self.clear_line(f"{''.join(self._line_buffer)}\n{self._last_status}\n")
                    else:
                        s = f"{''.join(self._line_buffer)}\n"
                else:
                    if self._last_status:
                        s = "\n"
                    else:
                        s = ""
                self._line_buffer.clear()
                self._last_status = ""
                if s:
                    self._stream.write(s)
                    self._stream.flush()

            return self._stream.close()

    def write(self, s: str) -> int:
        written = 0

        with self._lock:
            if self._stream.closed:
                raise ValueError("I/O operation on closed file.")

            if type(s) is ConsoleStatusMessage:
                s = s.strip("\r\n")
                if self._last_status:
                    self._last_status = s
                    s = self.clear_line(s)
                else:
                    self._last_status = s
                written = self._stream.write(s)
                self._stream.flush()

            elif lines := "".join(self._get_lines(s)):
                if self._last_status:
                    s = self.clear_line(f"{lines}{self._last_status}")
                else:
                    s = lines
                written = self._stream.write(s)

        return written


class ConsoleOutputStreamANSI(_ConsoleOutputStreamWithStatusMessages):
    _CR_CLREOL = "\r\x1b[K"

    def clear_line(self, s: str) -> str:
        return f"{self._CR_CLREOL}{s}"


class ConsoleOutputStreamWindows(_ConsoleOutputStreamWithStatusMessages):
    windows_console: WindowsConsole

    def clear_line(self, s: str) -> str:
        self.windows_console.clear_line()

        return s
