from typing import Dict

import requests

from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOIterWrapper, StreamIOThreadWrapper


VALID_ARGS = ("method", "url", "params", "headers", "cookies", "auth", "data", "json", "files")


def normalize_key(keyval):
    key, val = keyval
    key = hasattr(key, "decode") and key.decode("utf8", "ignore") or key

    return key, val


def valid_args(args):
    return {k: v for k, v in args.items() if k in VALID_ARGS}


class HTTPStream(Stream):
    """
    An HTTP stream using the :mod:`requests` library.
    """

    __shortname__ = "http"

    args: Dict
    """A dict of keyword arguments passed to :meth:`requests.Session.request`, such as method, headers, cookies, etc."""

    def __init__(
        self,
        session_,
        url: str,
        buffered: bool = True,
        **args
    ):
        """
        :param streamlink.Streamlink session_: Streamlink session instance
        :param url: The URL of the HTTP stream
        :param buffered: Wrap stream output in an additional reader-thread
        :param args: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session_)
        self.args = dict(url=url, **args)
        self.buffered = buffered

    def __repr__(self):
        return "<HTTPStream({0!r})>".format(self.url)

    def __json__(self):
        args = self.args.copy()
        method = args.pop("method", "GET")
        req = requests.Request(method=method, **valid_args(args))
        req = self.session.http.prepare_request(req)

        headers = dict(map(normalize_key, req.headers.items()))

        return dict(type=type(self).shortname(), url=req.url,
                    method=req.method, headers=headers,
                    body=req.body)

    @property
    def url(self) -> str:
        """
        The URL to the stream, prepared by :mod:`requests` with parameters read from :attr:`args`.
        """

        args = self.args.copy()
        method = args.pop("method", "GET")
        return requests.Request(method=method, **valid_args(args)).prepare().url

    def open(self):
        args = self.args.copy()
        method = args.pop("method", "GET")
        timeout = self.session.options.get("stream-timeout")
        res = self.session.http.request(
            method=method,
            stream=True,
            exception=StreamError,
            timeout=timeout,
            **valid_args(args)
        )

        fd = StreamIOIterWrapper(res.iter_content(8192))
        if self.buffered:
            fd = StreamIOThreadWrapper(self.session, fd, timeout=timeout)

        return fd

    def to_url(self):
        return self.url
