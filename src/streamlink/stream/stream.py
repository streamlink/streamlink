import io
import json
import logging

log = logging.getLogger(__name__)


class Stream(object):
    """
    This is a base class that should be inherited when implementing
    different stream types. Should only be created by plugins.
    """

    __shortname__ = "stream"

    @classmethod
    def shortname(cls):
        return cls.__shortname__

    def __init__(self, session):
        self.session = session

    def __repr__(self):
        params = [repr(self.shortname())]
        for method in self.to_url, self.to_manifest_url:
            try:
                params.append(repr(method()))
            except TypeError:
                pass

        return "<{0} [{1}]>".format(self.__class__.__name__, ', '.join(params))

    def __json__(self):
        return dict(type=self.shortname())

    @property
    def json(self):
        obj = self.__json__()
        return json.dumps(obj)

    def to_url(self):
        raise TypeError("<{0} [{1}]> cannot be translated to a URL".format(self.__class__.__name__, self.shortname()))

    def to_manifest_url(self):
        raise TypeError("<{0} [{1}]> cannot be translated to a manifest URL".format(self.__class__.__name__, self.shortname()))

    def open(self):
        # type: () -> "StreamIO"
        """
        Attempts to open a connection to the stream.
        Returns a file-like object that can be used to read the stream data.

        Raises :exc:`StreamError` on failure.
        """
        raise NotImplementedError


class StreamIO(io.IOBase):
    pass


__all__ = ["Stream", "StreamIO"]
