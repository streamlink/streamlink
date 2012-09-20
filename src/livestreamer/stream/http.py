from . import Stream, StreamError
from ..utils import urlget

class HTTPStream(Stream):
    def __init__(self, session, url, **args):
        Stream.__init__(self, session)

        self.url = url
        self.args = args

    def open(self):
        res = urlget(self.url, prefetch=False,
                     exception=StreamError,
                     **self.args)

        return res.raw

