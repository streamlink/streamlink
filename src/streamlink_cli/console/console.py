from __future__ import annotations

import sys
from contextlib import contextmanager, suppress
from getpass import getpass
from json import dumps
from typing import Any, TextIO

from streamlink_cli.console.stream import ConsoleOutputStream, ConsoleStatusMessage
from streamlink_cli.utils import JSONEncoder


class ConsoleOutput:
    def __init__(
        self,
        *,
        console_output: ConsoleOutputStream | None = None,
        file_output: TextIO | None = None,
        json: bool = False,
    ):
        self.json: bool = json
        self._console_output: ConsoleOutputStream | None = console_output
        self._supports_status_messages: bool = console_output is not None and console_output.supports_status_messages()
        self._file_output: TextIO | None = file_output

    @property
    def console_output(self) -> ConsoleOutputStream | None:
        return self._console_output

    @console_output.setter
    def console_output(self, console_output: ConsoleOutputStream | None) -> None:
        self._console_output = console_output
        self._supports_status_messages = console_output is not None and console_output.supports_status_messages()

    @property
    def file_output(self) -> TextIO | None:
        return self._file_output

    @file_output.setter
    def file_output(self, file_output: TextIO | None) -> None:
        if file_output is None or file_output.isatty():
            self._file_output = None
        else:
            self._file_output = file_output

    def supports_status_messages(self) -> bool:
        return self._supports_status_messages

    def close(self):
        if self._console_output:  # pragma: no branch
            with suppress(OSError):
                self._console_output.close()
            self._console_output.restore()
        if self._file_output:  # pragma: no branch
            with suppress(OSError):
                self._file_output.close()

    @staticmethod
    def _write(stream: TextIO, msg: str):
        with suppress(OSError):
            stream.write(msg)
            stream.flush()

    def _write_console(self, msg: str):
        if self._console_output is None:
            return
        self._write(self._console_output, msg)

    def _write_file(self, msg: str):
        if self._file_output is None:
            return
        self._write(self._file_output, msg)

    @contextmanager
    def _prompt(self):
        if not sys.stdin or not sys.stdin.isatty():
            raise OSError("No input TTY available")
        if not self._console_output or not self._console_output.isatty():
            raise OSError("No output TTY available")

        try:
            yield
        except OSError:
            raise
        except Exception as err:
            raise OSError(err) from err

    def ask(self, prompt: str) -> str:
        with self._prompt():
            self._write_console(prompt)
            return input().strip()

    def ask_password(self, prompt: str) -> str:
        with self._prompt():
            return getpass(prompt=prompt, stream=self._console_output)

    def msg(self, msg: str) -> None:
        if self.json:
            return
        msg = f"{msg}\n"
        self._write_console(msg)
        self._write_file(msg)

    def msg_status(self, msg: str) -> None:
        if self.json or not self._supports_status_messages:
            return
        self._write_console(ConsoleStatusMessage(msg))

    def msg_json(self, *objs: Any, **keywords: Any) -> None:
        if not self.json:
            return

        out: list | dict
        if objs and isinstance(objs[0], list):
            out = []
            for obj in objs:
                if isinstance(obj, list):
                    out.extend(obj)
                else:
                    if hasattr(obj, "__json__") and callable(obj.__json__):
                        obj = obj.__json__()
                    out.append(obj)
            if keywords:
                out.append(keywords)
        else:
            out = {}
            for obj in objs:
                if hasattr(obj, "__json__") and callable(obj.__json__):
                    obj = obj.__json__()
                if not isinstance(obj, dict):
                    continue
                out.update(**obj)
            out.update(**keywords)

        if self._console_output is not None:
            # don't escape Unicode characters outside the ASCII range if the output encoding is UTF-8
            ensure_ascii = self._console_output.encoding != "utf-8"
            msg = dumps(out, cls=JSONEncoder, ensure_ascii=ensure_ascii, indent=2)
            self._write_console(f"{msg}\n")

        if self._file_output is not None:
            msg = dumps(out, cls=JSONEncoder, ensure_ascii=False, indent=2)
            self._write(self._file_output, f"{msg}\n")
