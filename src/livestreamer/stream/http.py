from . import Stream, StreamIOWrapper, StreamError
from ..utils import urlget

from requests import Request

class HTTPStream(Stream):
    __shortname__ = "http"

    def __init__(self, session, url, **args):
        Stream.__init__(self, session)

        self.url = url
        self.args = args

    def __repr__(self):
        return "<HTTPStream({0!r})>".format(self.url)

    def __json__(self):
        req = Request(url=self.url, **self.args).prepare()

        return dict(type=HTTPStream.shortname(),
                    url=req.url, headers=req.headers,
                    body=req.body, method=req.method or "GET")

    def open(self):
        res = urlget(self.url, stream=True,
                     exception=StreamError,
                     **self.args)

        return StreamIOWrapper(res.raw)

