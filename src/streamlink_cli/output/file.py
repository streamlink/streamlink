from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from streamlink.compat import is_win32
from streamlink_cli.compat import stdout
from streamlink_cli.output.abc import Output


if is_win32:
    import msvcrt
    from os import O_BINARY  # type: ignore[attr-defined]


class FileOutput(Output):
    def __init__(
        self,
        filename: Path | None = None,
        fd: BinaryIO | None = None,
        record: FileOutput | None = None,
    ):
        super().__init__()
        self.filename = filename
        self.fd = fd
        self.record = record

    def _open(self):
        if self.filename:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            self.fd = self.filename.open("wb")

        if self.record:
            self.record.open()

        if is_win32:
            msvcrt.setmode(self.fd.fileno(), O_BINARY)

    def _close(self):
        if self.fd is not stdout:
            self.fd.close()
        if self.record:
            self.record.close()

    def _write(self, data):
        self.fd.write(data)
        if self.record:
            self.record.write(data)
