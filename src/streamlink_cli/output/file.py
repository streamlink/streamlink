from pathlib import Path
from typing import BinaryIO, Optional

from streamlink.compat import is_win32
from streamlink_cli.compat import stdout
from streamlink_cli.output.abc import Output


if is_win32:
    import msvcrt
    from os import O_BINARY


class FileOutput(Output):
    def __init__(
        self,
        filename: Optional[Path] = None,
        fd: Optional[BinaryIO] = None,
        record: Optional["FileOutput"] = None,
    ):
        super().__init__()
        self.filename = filename
        self.fd = fd
        self.record = record

    def _open(self):
        if self.filename:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            self.fd = open(self.filename, "wb")

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
