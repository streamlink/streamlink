import inspect

import requests

from .stream import Stream
from .wrappers import StreamIOThreadWrapper, StreamIOIterWrapper
from ..exceptions import StreamError


def normalize_key(keyval):
    key, val = keyval
    key = hasattr(key, "decode") and key.decode("utf8", "ignore") or key

    return key, val


def valid_args(args):
    argspec = inspect.getargspec(requests.Request.__init__)

    return dict(filter(lambda kv: kv[0] in argspec.args, args.items()))


class HTTPStream(Stream):
    """A HTTP stream using the requests library.

    *Attributes:*

    - :attr:`url`  The URL to the stream, prepared by requests.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
      to :meth:`requests.request`, such as headers and cookies.

    """

    __shortname__ = "http"

    def __init__(self, session_, url, buffered=True, **args):
        Stream.__init__(self, session_)

        self.args = dict(url=url, **args)
        self.buffered = buffered

    def __repr__(self):
        return "<HTTPStream({0!r})>".format(self.url)

    def __json__(self):
        method = self.args.get("method", "GET")
        req = requests.Request(method=method, **valid_args(self.args))

        # prepare_request is only available in requests 2.0+
        if hasattr(self.session.http, "prepare_request"):
            req = self.session.http.prepare_request(req)
        else:
            req = req.prepare()

        headers = dict(map(normalize_key, req.headers.items()))

        return dict(type=type(self).shortname(), url=req.url,
                    method=req.method, headers=headers,
                    body=req.body)

    @property
    def url(self):
        method = self.args.get("method", "GET")
        return requests.Request(method=method,
                                **valid_args(self.args)).prepare().url

    def open(self):
        method = self.args.get("method", "GET")
        timeout = self.session.options.get("http-timeout")
        res = self.session.http.request(method=method,
                                        stream=True,
                                        exception=StreamError,
                                        timeout=timeout,
                                        **self.args)

        fd = StreamIOIterWrapper(res.iter_content(8192))
        if self.buffered:
            fd = StreamIOThreadWrapper(self.session, fd, timeout=timeout)

        return fd

