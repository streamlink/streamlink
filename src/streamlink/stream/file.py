"""
Stream wrapper around a file
"""
from streamlink.stream import Stream


class FileStream(Stream):
    __shortname__ = "file"

    def __init__(self, session, path=None, fileobj=None):
        super(FileStream, self).__init__(session)
        self.path = path
        self.fileobj = fileobj
        if not self.path and not self.fileobj:
            raise ValueError("path or fileobj must be set")

    def open(self):
        return self.fileobj or open(self.path)
