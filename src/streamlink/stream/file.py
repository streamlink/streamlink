"""
Stream wrapper around a file
"""

from streamlink.stream.stream import Stream


class FileStream(Stream):
    __shortname__ = "file"

    def __init__(self, session, path=None, fileobj=None):
        super().__init__(session)
        self.path = path
        self.fileobj = fileobj
        if not self.path and not self.fileobj:
            raise ValueError("path or fileobj must be set")

    def __json__(self):  # noqa: PLW3201
        json = super().__json__()

        if self.path:
            json["path"] = self.path

        return json

    def to_url(self):
        if self.path is None:
            return super().to_url()

        return self.path

    def open(self):
        return self.fileobj or open(self.path, "rb")
