import io
import json
import logging

log = logging.getLogger(__name__)


class Stream(object):
    __shortname__ = "stream"

    """
    This is a base class that should be inherited when implementing
    different stream types. Should only be created by plugins.
    """

    def __init__(self, session):
        self.session = session

    def __repr__(self):
        return "<Stream()>"

    def __json__(self):
        return dict(type=type(self).shortname())

    def open(self):
        """
        Attempts to open a connection to the stream.
        Returns a file-like object that can be used to read the stream data.

        Raises :exc:`StreamError` on failure.
        """
        raise NotImplementedError

    @property
    def json(self):
        obj = self.__json__()
        return json.dumps(obj)

    @classmethod
    def shortname(cls):
        return cls.__shortname__

    def to_url(self):
        raise TypeError("{0} cannot be converted to a URL".format(self.shortname()))


class StreamIO(io.IOBase):
    pass


__all__ = ["Stream", "StreamIO"]
