"""
Stream wrapper around a file
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from streamlink.stream.stream import Stream


if TYPE_CHECKING:
    from io import BytesIO


class FileStream(Stream):
    __shortname__ = "file"

    path: Path | None
    fileobj: BytesIO | None

    def __init__(self, session, path: Path | str | None = None, fileobj: BytesIO | None = None):
        super().__init__(session)
        if path:
            self.path = Path(path)
            self.fileobj = None
        elif fileobj:
            self.path = None
            self.fileobj = fileobj
        else:
            raise ValueError("path or fileobj must be set")

    def __json__(self):  # noqa: PLW3201
        json = super().__json__()

        if self.path:
            json["path"] = str(self.path)

        return json

    def to_url(self):
        if self.path is None:
            return super().to_url()

        return str(self.path)

    def open(self):
        if self.fileobj:
            return self.fileobj
        elif self.path:  # pragma: no branch
            return self.path.open("rb")
